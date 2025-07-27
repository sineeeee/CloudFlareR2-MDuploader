import boto3
import requests
import os
import uuid
import re
from html.parser import HTMLParser
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

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

def extract_img_src_from_html(text):
    """
    从输入文本中提取所有<img>标签中的src链接和width属性
    """
    # 使用正则表达式匹配所有<img>标签
    pattern = r'<img\s+[^>]*>'
    img_tags = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
    
    results = []
    for img_tag in img_tags:
        parser = ImageHTMLParser()
        parser.feed(img_tag)
        if parser.img_src:
            results.append({
                'src': parser.img_src,
                'width': parser.img_width
            })
    return results

def upload_image_to_r2(image_url_or_html):
    """
    Downloads an image from a URL or HTML img tag, uploads it to Cloudflare R2,
    and returns the img tag result.
    """
    if not image_url_or_html:
        return None

    # Check if input is HTML containing <img> tag
    stripped_input = image_url_or_html.strip()
    if stripped_input.startswith('<img'):
        # Input is just an <img> tag
        parser = ImageHTMLParser()
        parser.feed(image_url_or_html)
        if not parser.img_src:
            return "❌ No valid img src found in HTML tag"
        image_url = parser.img_src
        width_attr = f' width="{parser.img_width}"' if parser.img_width else ''
    elif '<img' in stripped_input:
        # Input contains HTML, try to extract <img> tag from it
        # Use a simple approach to extract the first <img ...> tag substring
        img_tag_match = re.search(r'<img\s+[^>]*>', stripped_input)
        if not img_tag_match:
            return "❌ No valid img tag found in HTML input"
        img_tag = img_tag_match.group(0)
        parser = ImageHTMLParser()
        parser.feed(img_tag)
        if not parser.img_src:
            return "❌ No valid img src found in extracted img tag"
        image_url = parser.img_src
        width_attr = f' width="{parser.img_width}"' if parser.img_width else ''
    else:
        image_url = image_url_or_html
        width_attr = ''

    try:
        # Download the image from the URL
        print(f"Downloading image from: {image_url}")
        response = requests.get(image_url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes

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
        print(f"Saved locally to: {local_path}")

        # Upload the image to R2 from local file
        print(f"Uploading {filename} to R2 bucket: {BUCKET_NAME}...")
        with open(local_path, 'rb') as file_obj:
            client.upload_fileobj(
                file_obj,
                BUCKET_NAME,
                filename,
                ExtraArgs={'ACL': 'public-read', 'ContentType': response.headers.get('Content-Type', 'image/jpeg')}
            )

        # Construct the public URL of the uploaded image
        public_url = f"{CUSTOM_DOMAIN}/{filename}" # Using custom domain
        print(f"✅ Image uploaded successfully!")
        return f"<img src=\"{public_url}\"{width_attr} />"

    except requests.exceptions.RequestException as e:
        return f"❌ Error downloading image: {e}"
    except Exception as e:
        return f"❌ An error occurred: {e}"

def upload_image_with_width(image_url, width):
    """
    上传图片并返回带指定width的img标签
    """
    try:
        # Download the image from the URL
        print(f"Downloading image from: {image_url}")
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
        print(f"Saved locally to: {local_path}")

        # Upload the image to R2 from local file
        print(f"Uploading {filename} to R2 bucket: {BUCKET_NAME}...")
        with open(local_path, 'rb') as file_obj:
            client.upload_fileobj(
                file_obj,
                BUCKET_NAME,
                filename,
                ExtraArgs={'ACL': 'public-read', 'ContentType': response.headers.get('Content-Type', 'image/jpeg')}
            )

        # Construct the public URL of the uploaded image
        public_url = f"{CUSTOM_DOMAIN}/{filename}"
        print(f"✅ Image uploaded successfully!")
        
        width_attr = f' width="{width}"' if width else ''
        return f"<img src=\"{public_url}\"{width_attr} />"

    except requests.exceptions.RequestException as e:
        return f"❌ Error downloading image: {e}"
    except Exception as e:
        return f"❌ An error occurred: {e}"

def process_input(input_text):
    """
    处理输入文本，支持单个URL、单个img标签、或多个<img>标签
    """
    stripped_input = input_text.strip()
    
    # 检查是否包含<img>标签
    if '<img' in stripped_input:
        print("检测到<img>标签，正在提取图片链接...")
        img_infos = extract_img_src_from_html(stripped_input)
        if not img_infos:
            print("❌ 未在HTML中找到有效的img标签")
            return
        
        print(f"找到 {len(img_infos)} 个图片，开始批量处理...")
        results = []
        
        for i, img_info in enumerate(img_infos, 1):
            print(f"\n--- 处理第 {i} 个图片: {img_info['src']} ---")
            result = upload_image_with_width(img_info['src'], img_info['width'])
            if result:
                results.append(result)
        
        print(f"\n🎉 批量处理完成！共处理 {len(img_infos)} 个图片")
        print("=" * 50)
        print("所有结果:")
        print(" ".join(results))
        print("=" * 50)
    else:
        # 单个URL
        result = upload_image_to_r2(stripped_input)
        if result:
            print(f"\n{result}\n")

if __name__ == "__main__":
    print("--- Cloudflare R2 Image Uploader ---")
    print("支持输入:")
    print("1. 单个图片URL")
    print("2. 单个<img>标签")
    print("3. 多个<img>标签（包含在HTML中）")
    print("输入 'exit' 或 'quit' 退出程序")
    print()
    
    while True:
        user_input = input("请输入 > ")
        if user_input.lower() in ['exit', 'quit']:
            break
        process_input(user_input)
