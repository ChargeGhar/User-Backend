# Screen Cabinet Advertising API Documentation

## API Endpoint
```
GET /api/advert/rentbox/distribute/list
```

### Device Request Example
```
https://s.besiter.com.cn/sw/iot/api/advert/rentbox/distribute/list?uuid=867329047299180&sign=3c61d5365ac4348d842ffe05a67eb6e1
```

---

## Request Parameters

| Parameter | Type   | Required | Description |
|----------|--------|----------|-------------|
| uuid | String | Yes | Device IMEI |
| sign | String | Yes | Signature, `md5(uuid=867329047299180)` |

---

## Response Example

```json
{
  "code": 200,
  "type": 0,
  "data": [
    {
      "id": 10002348,
      "title": "",
      "fileType": 0,
      "url1": "",
      "url2": "http://sharingweb.oss-cn-shenzhen.aliyuncs.com/images/2588e922e8d4e68173081511adced4e0.png",
      "url3": "",
      "forward": "",
      "playTime": 5,
      "weight": 0,
      "screenBrightness": 255,
      "guuid": null
    }
  ],
  "msg": "OK",
  "time": 1742813624719
}
```

---

## Response Fields

### Top-level Fields

| Field | Type | Description |
|------|------|-------------|
| code | Integer | Response code, `200` indicates success |
| type | Integer | Type, default `0` |
| data | Array | Advertising data list |
| msg | String | Response message |
| time | Long | Server timestamp |

---

### Data Object Fields

| Field | Type | Default | Description |
|------|------|---------|-------------|
| id | Long | 0 / Not returned | Device ID |
| title | String | `""` | Advertisement title |
| fileType | Integer | `0` | File type |
| url1 | String | `""` | **Advertisement URL for devices with fewer than 20 slots** (supports `jpg / png / mp4`) |
| url2 | String | `""` | **Advertisement URL for devices with more than 20 slots** (supports `jpg / png / mp4`) |
| url3 | String | `""` | Reserved field |
| forward | String | `""` / Not returned | Reserved field |
| playTime | Integer | `5` | Image carousel duration (seconds) |
| weight | Integer | `0` | Volume level, range `0 - 100` |
| screenBrightness | Integer | `0` | Screen brightness, range `0 - 255` |
| guuid | String | `null` | Reserved field |

---

## Notes

- Use `url1` or `url2` depending on the number of device slots
- Supported image formats: `jpg`, `png`
- Supported video format: `mp4`
- `playTime` applies only to image rotation
- Ad update instructions: load_ad, example: {"cmd":"load_ad"}
