from flask import Flask, render_template, request, jsonify
import boto3
import requests
import os
import uuid
import re
from html.parser import HTMLParser
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 从环境变量读取 Cloudflare R2 配置
ACCESS_KEY_ID = os.getenv('ACCESS_KEY_ID')
SECRET_ACCESS_KEY = os.getenv('SECRET_ACCESS_KEY')
ENDPOINT_URL = os.getenv('ENDPOINT_URL')
BUCKET_NAME = os.getenv('BUCKET_NAME')
CUSTOM_DOMAIN = os.getenv('CUSTOM_DOMAIN', 'https://your-domain.com')

# 检查必要的环境变量
if not all([ACCESS_KEY_ID, SECRET_ACCESS_KEY, ENDPOINT_URL, BUCKET_NAME]):
    raise ValueError("请在 .env 文件中配置所有必要的环境变量: ACCESS_KEY_ID, SECRET_ACCESS_KEY, ENDPOINT_URL, BUCKET_NAME")

# Initialize a session using S3-compatible API
session = boto3.session.Session()
client = session.client('s3',
                        region_name='auto',
                        endpoint_url=ENDPOINT_URL,
                        aws_access_key_id=ACCESS_KEY_ID,
                        aws_secret_access_key=SECRET_ACCESS_KEY)

class ImageHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.img_src = None
        self.img_width = None
    
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            for attr, value in attrs:
                if attr == 'src':
                    self.img_src = value
                elif attr == 'width':
                    self.img_width = value

def upload_single_image(image_url):
    """
    上传单个图片到R2并返回新的URL
    """
    try:
        print(f"正在下载图片: {image_url}")
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        # Create downloads directory if not exists
        os.makedirs('downloads', exist_ok=True)

        # Generate a random filename while preserving the extension
        original_filename = os.path.basename(image_url.split('?')[0])
        file_extension = os.path.splitext(original_filename)[1]
        random_filename = f"{uuid.uuid4()}{file_extension}"
        filename = random_filename

        # Save image locally
        local_path = os.path.join('downloads', filename)
        with open(local_path, 'wb') as f:
            f.write(response.content)

        # Upload the image to R2 from local file
        print(f"正在上传 {filename} 到 R2...")
        with open(local_path, 'rb') as file_obj:
            client.upload_fileobj(
                file_obj,
                BUCKET_NAME,
                filename,
                ExtraArgs={'ACL': 'public-read', 'ContentType': response.headers.get('Content-Type', 'image/jpeg')}
            )

        # Construct the public URL of the uploaded image
        public_url = f"{CUSTOM_DOMAIN}/{filename}"
        print(f"✅ 图片上传成功: {public_url}")
        return public_url

    except Exception as e:
        print(f"❌ 上传图片失败: {e}")
        return None

def extract_images_from_markdown(text):
    """
    从markdown文本中提取所有图片信息
    支持markdown语法 ![alt](url) 和 HTML img标签，以及包含在<a>标签中的img标签
    """
    images = []
    
    # 提取markdown图片语法 ![alt](url)
    markdown_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    markdown_matches = re.finditer(markdown_pattern, text)
    for match in markdown_matches:
        images.append({
            'type': 'markdown',
            'full_match': match.group(0),
            'alt': match.group(1),
            'url': match.group(2),
            'start': match.start(),
            'end': match.end()
        })
    
    # 优先提取包含在<a>标签中的<img>标签
    a_img_pattern = r'<a\s+[^>]*>\s*<img\s+[^>]*>\s*</a>'
    a_img_matches = re.finditer(a_img_pattern, text, re.IGNORECASE | re.DOTALL)
    for match in a_img_matches:
        full_a_tag = match.group(0)
        # 从<a>标签中提取<img>标签
        img_pattern_in_a = r'<img\s+[^>]*>'
        img_match = re.search(img_pattern_in_a, full_a_tag, re.IGNORECASE)
        if img_match:
            img_tag = img_match.group(0)
            parser = ImageHTMLParser()
            parser.feed(img_tag)
            if parser.img_src:
                images.append({
                    'type': 'a_img',  # 新类型：包含在a标签中的img
                    'full_match': full_a_tag,
                    'img_tag': img_tag,
                    'url': parser.img_src,
                    'width': parser.img_width,
                    'start': match.start(),
                    'end': match.end()
                })
    
    # 提取单独的HTML img标签（不在<a>标签中的）
    img_pattern = r'<img\s+[^>]*>'
    img_matches = re.finditer(img_pattern, text, re.IGNORECASE)
    for match in img_matches:
        img_tag = match.group(0)
        
        # 检查这个img标签是否已经被包含在a标签中处理过了
        already_processed = False
        for existing_img in images:
            if (existing_img['type'] == 'a_img' and 
                match.start() >= existing_img['start'] and 
                match.end() <= existing_img['end']):
                already_processed = True
                break
        
        if not already_processed:
            parser = ImageHTMLParser()
            parser.feed(img_tag)
            if parser.img_src:
                images.append({
                    'type': 'html',
                    'full_match': img_tag,
                    'url': parser.img_src,
                    'width': parser.img_width,
                    'start': match.start(),
                    'end': match.end()
                })
    
    # 按位置排序，从后往前处理避免位置偏移
    images.sort(key=lambda x: x['start'], reverse=True)
    return images

def process_markdown_article(markdown_text):
    """
    处理markdown文章中的所有图片
    """
    print("开始处理markdown文章...")
    images = extract_images_from_markdown(markdown_text)
    
    if not images:
        return {
            'success': True,
            'message': '未发现需要处理的图片',
            'processed_text': markdown_text,
            'processed_count': 0
        }
    
    print(f"发现 {len(images)} 个图片，开始处理...")
    processed_text = markdown_text
    processed_count = 0
    failed_images = []
    
    for i, img_info in enumerate(images):
        print(f"\n--- 处理第 {i+1} 个图片: {img_info['url']} ---")
        new_url = upload_single_image(img_info['url'])
        
        if new_url:
            # 替换原来的图片标签
            if img_info['type'] == 'markdown':
                # 替换markdown语法
                new_tag = f"![{img_info['alt']}]({new_url})"
            elif img_info['type'] == 'a_img':
                # 替换包含在a标签中的img标签，去掉整个a标签
                width_attr = f' width="{img_info["width"]}"' if img_info.get('width') else ''
                new_tag = f'<img src="{new_url}"{width_attr} />'
            else: # html img tag
                # 替换HTML img标签
                width_attr = f' width="{img_info["width"]}"' if img_info.get('width') else ''
                new_tag = f'<img src="{new_url}"{width_attr} />'
            
            # 从后往前替换，避免位置偏移
            processed_text = (
                processed_text[:img_info['start']] + 
                new_tag + 
                processed_text[img_info['end']:]
            )
            processed_count += 1
        else:
            failed_images.append(img_info['url'])
    
    result = {
        'success': True,
        'processed_text': processed_text,
        'processed_count': processed_count,
        'total_count': len(images)
    }
    
    if failed_images:
        result['message'] = f"成功处理 {processed_count} 个图片，{len(failed_images)} 个失败"
        result['failed_images'] = failed_images
    else:
        result['message'] = f"成功处理所有 {processed_count} 个图片"
    
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        data = request.get_json()
        markdown_text = data.get('markdown', '')
        
        if not markdown_text.strip():
            return jsonify({
                'success': False,
                'message': '请输入markdown内容'
            })
        
        result = process_markdown_article(markdown_text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理出错: {str(e)}'
        })

@app.route('/upload_local', methods=['POST'])
def upload_local():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})
    if file:
        try:
            # Create downloads directory if not exists
            os.makedirs('downloads', exist_ok=True)
            
            filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
            
            # Save the file to a temporary location
            temp_path = os.path.join('downloads', filename)
            file.save(temp_path)

            # Upload to R2
            with open(temp_path, 'rb') as file_obj:
                client.upload_fileobj(
                    file_obj,
                    BUCKET_NAME,
                    filename,
                    ExtraArgs={'ACL': 'public-read', 'ContentType': file.content_type}
                )
            
            # Clean up the temporary file
            os.remove(temp_path)

            public_url = f"{CUSTOM_DOMAIN}/{filename}"
            return jsonify({'success': True, 'url': public_url})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'})

@app.route('/console_process', methods=['POST'])
def console_process():
    try:
        data = request.get_json()
        user_input = data.get('input', '').strip()
        
        if not user_input:
            return jsonify({
                'success': False,
                'message': '请输入内容'
            })
        
        # 处理单个图片输入（类似upload.py的逻辑）
        result = process_single_input(user_input)
        
        if result.startswith('❌'):
            return jsonify({
                'success': False,
                'message': result
            })
        else:
            return jsonify({
                'success': True,
                'result': result
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理出错: {str(e)}'
        })

def process_single_input(input_text):
    """
    处理单个输入（URL或HTML标签），返回处理后的img标签
    """
    if not input_text:
        return "❌ 输入为空"

    # 检查输入类型
    stripped_input = input_text.strip()
    if stripped_input.startswith('<img'):
        # 输入是img标签
        parser = ImageHTMLParser()
        parser.feed(input_text)
        if not parser.img_src:
            return "❌ 未找到有效的img src"
        image_url = parser.img_src
        width_attr = f' width="{parser.img_width}"' if parser.img_width else ''
    elif '<img' in stripped_input:
        # 输入包含HTML，提取img标签
        img_tag_match = re.search(r'<img\s+[^>]*>', stripped_input, re.IGNORECASE)
        if not img_tag_match:
            return "❌ 未找到有效的img标签"
        img_tag = img_tag_match.group(0)
        parser = ImageHTMLParser()
        parser.feed(img_tag)
        if not parser.img_src:
            return "❌ 未找到有效的img src"
        image_url = parser.img_src
        width_attr = f' width="{parser.img_width}"' if parser.img_width else ''
    else:
        # 假设是直接的URL
        image_url = stripped_input
        width_attr = ''

    # 上传图片
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        # 确保downloads目录存在
        os.makedirs('downloads', exist_ok=True)

        # 生成随机文件名
        original_filename = os.path.basename(image_url.split('?')[0])
        file_extension = os.path.splitext(original_filename)[1]
        if not file_extension:
            file_extension = '.jpg'  # 默认扩展名
        random_filename = f"{uuid.uuid4()}{file_extension}"
        filename = random_filename

        # 本地保存
        local_path = os.path.join('downloads', filename)
        with open(local_path, 'wb') as f:
            f.write(response.content)

        # 上传到R2
        with open(local_path, 'rb') as file_obj:
            client.upload_fileobj(
                file_obj,
                BUCKET_NAME,
                filename,
                ExtraArgs={'ACL': 'public-read', 'ContentType': response.headers.get('Content-Type', 'image/jpeg')}
            )

        # 清理本地文件
        os.remove(local_path)

        # 构建公开URL
        public_url = f"{CUSTOM_DOMAIN}/{filename}"
        return f"<img src=\"{public_url}\"{width_attr} />"

    except requests.exceptions.RequestException as e:
        return f"❌ 下载图片失败: {e}"
    except Exception as e:
        return f"❌ 处理失败: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)