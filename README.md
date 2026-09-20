# LiftBay

电梯派梯：同向优先与楼层距离评分，轿厢满员拒绝派工，楼栋可设禁停层。

## 禁停层

- 楼栋页可把任意楼层标记/取消为禁停层，保存后再次进入仍在。
- 禁停层不能登记呼梯（呼梯页下拉中不可选，直接提交接口返回 400）。
- 派工不会把轿厢停到禁停层，拒绝原因与回放日志区分"禁停层"与"轿厢满员"。
- 禁停层不产生候梯候选，不计入拥堵统计。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4200 |
| API | http://localhost:9200 |
| API 文档 | http://localhost:9200/docs |
| Postgres | localhost:5443 |

健康检查：`GET http://localhost:9200/api/health`

## 页面

- `/buildings` — 楼栋
- `/cars` — 轿厢
- `/calls` — 呼梯
- `/dispatch` — 派工
- `/replay` — 回放
- `/congestion` — 拥堵

## 使用说明

1. 查看楼栋与轿厢状态。
2. 在呼梯页登记请求，在派工页按评分分配轿厢。
3. 回放页查看派工轨迹，拥堵页查看高峰楼层。

## 开发与测试

```bash
docker compose exec api pytest -q
```
