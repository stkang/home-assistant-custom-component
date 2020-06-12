# HomeAssistant Custom Component

* HomeAssistant 0.110.7 버전에서 테스트 완료되었습니다.

## Enertalk (에너톡)
<pre>
configuration.yaml

enertalk:
  client_id: !secret enertalk_client_id
  client_secret: !secret enertalk_client_secret
  real_time_interval: 30
  billing_interval: 1800
  monitored_conditions:
    - real_time_usage
    - today_usage
    - today_charge
    - yesterday_usage
    - yesterday_charge
    - month_usage
    - month_charge
    - estimate_usage
    - estimate_charge
</pre>

## AirKorea 공기오염정보료
<pre>
sensor:
  - platform: airkorea
    name: airkorea
    service_key: !secret air_korea_service_key
    station_name: 대왕판교로(백현동)
    monitored_conditions:
      - data_time
      - so2
      - co
      - no2
      - pm10
      - pm10_grade
      - pm25
      - pm25_grade
      - khai
      - khai_grade
</pre>

## 귀뚜라미 IOT 보일러
<pre>
climate:
  - platform: kiturami
    name: kiturami
    username: !secret default_username
    password: !secret default_password
    scan_interval: 1800
</pre>

## 샤오미 제습기
<pre>
climate:
  - platform: kiturami
    name: kiturami
    username: !secret default_username
    password: !secret default_password
    scan_interval: 1800
</pre>

## SK 날씨정보(지원 종료)


**네이버 페이 후원하기**
- http://npay.to/975894e97ffd4b1f3c4a
