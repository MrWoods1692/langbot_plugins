# 全球时区查询API
双英文UST和CST标准时区
- **接口地址**: https://yunzhiapi.cn/API/qqsqcx.php
- **请求方式**: GET/POST
- **返回格式**: JSON/TEXT
- **请求示例**: https://yunzhiapi.cn/API/qqsqcx.php?country=美国&kind=UST
## 请求参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| token | string | 是 | 登录获取用户密钥 |
| country | string | 是 | 国家名称，支持中文和英文 |
| kind | string | 是 | 获取的时区类型，填写UST（美国时区）或 CST（中国标准时间） |
| type | string | 否 | 返回的数据格式，支持json和text，不填写则默认为json |

## 返回参数
| 字段 | 类型 | 说明 |
|------|------|------|
| country_cn | string | 中文国家名称 |
| country_en | string | 英文国家名称 |
| capital | string | 国家首都 |
| timezone | string | 标准时区标识 |
| kind_tz_city | string | 代表城市 |

示例返回数据：{
    "success": true,
    "error": false,
    "code": 200,
    "data": {
        "country_cn": "美国",
        "country_en": "United States",
        "capital": "Washington D.C.",
        "timezone": "America/New_York",
        "utc_offset": "-04:00",
        "kind": "UST",
        "kind_tz_name": "AST (Atlantic Standard Time)",
        "kind_tz_name_cn": "大西洋标准时间",
        "kind_tz_offset": "-04:00",
        "kind_tz_city": "San Juan",
        "local_time": "2026-06-08 05:09:51",
        "converted_time": "2026-06-08 05:09:51",
        "time_diff": "AST 与本地时间相同",
        "query_time_utc": "2026-06-08 09:09:51",
        "query_time_beijing": "2026-06-08 17:09:51"
    }
}

## 示例代码
