> 除了这一句话的内容完全由AI生成

# 🚀 Markdown 图片上传器

一个基于 Flask 的现代化图片上传工具，支持 Markdown 批量处理、本地文件上传和控制台交互。自动将图片上传到 Cloudflare R2 存储服务。

## ✨ 功能特性

### 📝 Markdown 批量处理
- 自动识别并处理 Markdown 文章中的所有图片
- 支持多种格式：`![alt](url)`、`<img>`标签、超链接包装的图片
- 批量上传并替换为新的 R2 链接
- 保留图片的 width 等属性
- 自动去除超链接包装，只保留图片

### 📤 本地图片上传
- 支持拖拽和点击上传
- 批量上传多个文件
- 实时上传进度显示
- 每个图片提供三种格式输出：
  - **URL**：直接链接
  - **Markdown**：`![filename](url)` 格式
  - **HTML**：`<img src="url" alt="filename" />` 格式
- 一键复制任意格式

### 🖥️ 控制台交互
- 命令行风格的交互界面
- 支持直接输入图片URL或HTML标签
- 内置 `help` 和 `clear` 命令
- 实时处理反馈

## 🛠️ 安装与配置

### 环境要求
- Python 3.7+
- pip 包管理器

### 快速开始

1. **克隆项目**
```bash
git clone <your-repo-url>
cd cfr2uploader
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**

创建 `.env` 文件：
```bash
# Cloudflare R2 配置
ACCESS_KEY_ID=你的ACCESS_KEY_ID
SECRET_ACCESS_KEY=你的SECRET_ACCESS_KEY
ENDPOINT_URL=你的ENDPOINT_URL
BUCKET_NAME=你的BUCKET_NAME
CUSTOM_DOMAIN=你的自定义域名

# 示例:
# ACCESS_KEY_ID=123
# SECRET_ACCESS_KEY=321
# ENDPOINT_URL=https://123.r2.cloudflarestorage.com
# BUCKET_NAME=blog
# CUSTOM_DOMAIN=https://your-domain.com
```

4. **启动应用**
```bash
python run.py
# 或者直接运行
python app.py
```

5. **访问应用**
- 本地访问：http://localhost:5001
- 局域网访问：http://你的IP:5001

## 📁 项目结构

```
cfr2uploader/
├── app.py                 # Flask 主应用
├── upload.py             # 原始命令行版本
├── run.py                # 快速启动脚本
├── requirements.txt      # 项目依赖
├── .env                  # 环境变量配置
├── templates/
│   └── index.html        # Web UI 界面
├── downloads/            # 临时文件目录
└── README.md             # 项目说明
```

## 🔧 核心代码逻辑

### 图片识别与处理

```python
def extract_images_from_markdown(text):
    """
    从markdown文本中提取所有图片信息
    支持三种格式：
    1. Markdown语法: ![alt](url)
    2. HTML img标签: <img src="url" />
    3. 超链接图片: <a href="..."><img src="..." /></a>
    """
    images = []
    
    # 1. 提取 Markdown 图片语法
    markdown_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    # 2. 优先处理包含在<a>标签中的<img>
    a_img_pattern = r'<a\s+[^>]*>\s*<img\s+[^>]*>\s*</a>'
    
    # 3. 处理独立的HTML img标签
    img_pattern = r'<img\s+[^>]*>'
    
    # 按位置排序，从后往前替换避免位置偏移
    return sorted(images, key=lambda x: x['start'], reverse=True)
```

### 图片上传流程

```python
def upload_single_image(image_url):
    """
    图片上传核心流程：
    1. 下载原图片
    2. 生成随机文件名
    3. 临时保存到本地
    4. 上传到 Cloudflare R2
    5. 清理本地文件
    6. 返回公开URL
    """
    # 下载 → 保存 → 上传 → 清理
```

## 🌐 API 接口文档

### 1. Markdown 批量处理

**POST** `/process`

```json
// 请求
{
    "markdown": "# 标题\n![图片](https://example.com/image.jpg)"
}

// 响应
{
    "success": true,
    "message": "成功处理所有 1 个图片",
    "processed_text": "# 标题\n![图片](https://your-domain.com/xxx.jpg)",
    "processed_count": 1,
    "total_count": 1
}
```

### 2. 本地文件上传

**POST** `/upload_local`

```bash
# 使用 FormData 上传文件
curl -X POST -F "file=@image.jpg" http://localhost:5001/upload_local
```

```json
// 响应
{
    "success": true,
    "url": "https://your-domain.com/xxx.jpg"
}
```

### 3. 控制台处理

**POST** `/console_process`

```json
// 请求
{
    "input": "https://example.com/image.jpg"
}

// 响应
{
    "success": true,
    "result": "<img src=\"https://your-domain.com/xxx.jpg\" />"
}
```

## 🎯 使用场景

### 场景1：博客文章图片迁移
```markdown
# 原文章
![我的图片](https://other-site.com/image.jpg)

# 处理后
![我的图片](https://your-domain.com/uuid.jpg)
```

### 场景2：批量处理HTML中的图片
```html
<!-- 原始HTML -->
<a href="https://imgbox.com/abc"><img src="https://images.imgbox.com/abc.jpg" width="50%" /></a>

<!-- 处理后 -->
<img src="https://your-domain.com/uuid.jpg" width="50%" />
```

### 场景3：快速上传单张图片
在控制台标签页直接输入URL或拖拽文件，立即获得三种格式的输出。

## 🔒 Cloudflare R2 配置

### 获取 R2 凭证

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 "R2 Object Storage"
3. 创建存储桶
4. 获取 API 令牌：
   - `ACCESS_KEY_ID`: R2 访问密钥ID
   - `SECRET_ACCESS_KEY`: R2 访问密钥
   - `ENDPOINT_URL`: R2 端点URL
   - `BUCKET_NAME`: 存储桶名称

### 自定义域名设置

在 R2 控制台为存储桶绑定自定义域名，例如：`https://your-domain.com`

## 🚀 部署选项

### 本地开发
```bash
python app.py
# 访问：http://localhost:5001
```

### 局域网共享
应用自动绑定到 `0.0.0.0`，局域网内设备可通过内网IP访问。

### 生产部署

**使用 Gunicorn:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

**使用 Docker:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "app:app"]
```

**使用 Nginx 反向代理:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🐛 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 修改 app.py 中的端口
   app.run(debug=True, host='0.0.0.0', port=5002)
   ```

2. **环境变量未加载**
   ```bash
   # 确保 .env 文件存在且格式正确
   # 检查 python-dotenv 是否安装
   pip install python-dotenv
   ```

3. **图片上传失败**
   - 检查 R2 凭证是否正确
   - 确认存储桶权限设置
   - 查看控制台错误信息

4. **依赖安装失败**
   ```bash
   # 升级 pip
   pip install --upgrade pip
   # 使用国内镜像
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
   ```

## 📝 依赖说明

```txt
Flask==2.3.3          # Web 框架
boto3==1.34.0         # AWS SDK，用于 R2 操作
requests==2.31.0      # HTTP 请求库
python-dotenv==1.0.0  # 环境变量管理
```

---

**🎉 享受使用！如果这个工具对你有帮助，请给个 ⭐️ Star！** 
