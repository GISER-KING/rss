from app.core.config import API_KEY, API_BASE_URL, MODEL_ID, MODEL_PROVIDER
print('✓ 配置加载成功')
print(f'  提供商: {MODEL_PROVIDER}')
print(f'  模型: {MODEL_ID}')
print(f'  API地址: {API_BASE_URL}')
print(f'  API密钥: {API_KEY[:20]}...' if API_KEY else '  API密钥: 未设置')
