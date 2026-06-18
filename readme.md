# ============================================
#  Content Security Agent 启动指南
#  内容安全监控与分析智能体 - V1.1
# ============================================
# 
#  访问地址:
#    仪表盘:    http://localhost:8100/dashboard
#    API 文档:  http://localhost:8100/docs
#    健康检查:  http://localhost:8100/healthz
#
#  微信通知配置:
#    1. 注册 Server酱: https://sct.ftqq.com/
#    2. 获取 SendKey
#    3. 填入 .env 中的 SERVERCHAN_SENDKEY
# ============================================

# 第一步：进入项目目录
cd content-security-agent

# 第二步：安装依赖
pip install -r requirements.txt

# 第三步：填充演示数据（可选，如果你想要已有数据可以跑这个）
python seed.py

# 第四步：配置 .env 文件
#   - 填写 OPENAI_API_KEY（必填）
#   - 填写 SERVERCHAN_SENDKEY（可选，用于微信通知）
#   - 默认使用阿里云 DashScope 兼容接口

# 第五步：启动服务（必须在此目录下运行）
cd content-security-agent
python main.py

# 或者
uvicorn main:app --reload --port 8100

# 第六步：打开浏览器
#   http://localhost:8100/dashboard
#
# ============================================
#  功能标签页说明
# ============================================
#
#  🔍 内容安全分析  - AI 分析文本风险、生成运营策略
#  📅 日程管理      - 添加日程，提前 6 小时微信提醒
#  🚨 告警列表      - 高风险告警历史记录
#  ⚡ 异常检测      - P0: Z-score 统计异常检测 + 突增警报
#  📊 漏斗分析      - P2: 用户行为漏斗 + 留存率 + 行为分析
#  📋 报表生成      - P1: 日报/周报/月报自动生成 + AI 运营建议
#  ⚙️ 规则引擎      - P3: 可配置智能风控规则，支持开关
#
# ============================================
#  API 接口说明
# ============================================
#
#  POST /api/analyze       内容安全分析（自动触发规则）
#  POST /api/schedule       添加日程提醒
#  GET  /api/schedules      查看所有日程
#  DELETE /api/schedule/{id} 删除日程
#  GET  /api/dashboard      仪表盘数据
#  GET  /api/alerts         告警列表
#  POST /api/notify         手动发送微信通知
#  POST /api/anomaly/detect 异常检测
#  POST /api/report/generate 生成报表
#  POST /api/funnel         漏斗分析
#  GET  /api/retention      留存分析
#  GET  /api/user-behavior  用户行为分析
#  GET  /api/rules          规则列表
#  POST /api/rules/toggle   切换规则启用/禁用
#  GET  /api/rules/logs     规则执行日志
#
# ============================================
#  停止服务
# ============================================
#  Ctrl + C
