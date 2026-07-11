# TimezoneQueryPlugin

全球时区查询插件 — 基于 [yunzhiapi.cn](https://yunzhiapi.cn) 的 API，查询 UST（美国时区）和 CST（中国标准时间）等标准时区信息。

## 用法

```
!timezone <国家名称> <UST|CST>
```

或使用别名：

```
!tz <国家名称> <UST|CST>
```

## 示例

```
!timezone 美国 UST
!timezone 中国 CST
!tz 日本 UST
```

## 时区类型

| 类型 | 说明 |
|------|------|
| UST | 美国时区（US Time） |
| CST | 中国标准时间（China Standard Time） |

## 配置

需要在插件设置中填写 `api_token`，从 [yunzhiapi.cn](https://yunzhiapi.cn) 获取。