# XPUOJ API 逆向分析结果

## 基础信息

- **前端框架**: React 18 + Semantic UI + MobX + Axios
- **后端**: QDUOJ (Lyrio) 架构
- **API 基地址**: `https://sd629vuj4f7uh2cscrbe0.apigateway-cn-beijing.volceapi.com`
- **认证方式**: JWT Token (通过 Authorization header 或 URL 参数传递)
- **请求格式**: 全部 JSON (`application/json`)
- **无验证码**: `recaptchaEnabled: false`
- **无 CSRF**: 无 CSRF token 机制

## API 接口清单

### 1. 获取服务器配置
```
GET /api/auth/getSessionInfo?jsonp=1&token={token}
```
- 无 token 时获取服务器默认配置
- 有 token 时返回用户 session 信息

### 2. 登录
```
POST /api/auth/login
Body: {"email": "xxx@xxx.com", "password": "xxx"}
```
- 响应中包含 JWT token
- Token 格式: `eyJhbGciOiJIUzI1NiJ9.{base64_payload}.{signature}`

### 3. 查询比赛列表
```
POST /api/contest/queryContest
Body: {"skipCount": 0, "takeCount": 20}
```

### 4. 获取比赛详情
```
POST /api/contest/getContest
Body: {"id": 4}
```

### 5. 获取比赛题目列表
```
POST /api/contest/getContestProblems
Body: {"contestId": 4, "locale": "zh_CN"}
```

### 6. 获取题目详情
```
POST /api/contest/play/getProblem
Body: {
    "contestId": 4,
    "problemOrder": 1,
    "localizedContentsOfLocale": "zh_CN",
    "samples": true,
    "judgeInfo": true,
    "judgeInfoToBePreprocessed": true,
    "lastSubmissionAndLastAcceptedSubmission": true
}
```

### 7. 提交代码 ⭐
```
POST /api/contest/play/submit
Body: {
    "contestId": 4,
    "problemOrder": 1,
    "content": {
        "code": "代码内容..."
    }
}
```
- 响应应包含 submissionId

### 8. 查询提交结果
```
POST /api/submission/getSubmissionDetail
Body: {"submissionId": "5369", "locale": "zh_CN"}
```

### 9. 查询提交列表
```
POST /api/contest/play/querySubmissions
Body: {"locale": "zh_CN", "contestId": 4, "maxId": 5369, "takeCount": 1}
```

## 认证流程

1. POST `/api/auth/login` → 获取 token
2. 后续所有请求在 header 中携带: `Authorization: Bearer {token}`
3. 或通过 URL 参数 `token=xxx` 传递
