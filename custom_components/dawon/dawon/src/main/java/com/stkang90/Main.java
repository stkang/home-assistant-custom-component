package com.stkang90;

import java.io.DataOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketAddress;
import java.net.SocketException;
import java.util.Scanner;

public class Main {
    private static String wifiName = null;
    private static String wifiPasswd = null;

    private static String mqttIp = null;
    private static Integer mqttPort = 1883;
    private static String mqttPasswd = null;

    private static String deviceIp = "192.168.43.1";
    private static int devicePort = 5000;

    private static String deviceModelName = "B540-WF";
    private static String deviceModel = "B5X";

    private static Scanner sc;

    public static void main(String[] args) {
        System.out.println("###############################################");
        System.out.println("######### [Dawon Dns 스마트 플러그 설정 툴] #########");
        System.out.println("###############################################");
        System.out.println("## 테스트 성공 모델: Smart Plug(B530-WF/B540-WF), Smart Solar Power Generation Plug(B400-W) ##");
        System.out.println();

        sc = new Scanner(System.in);
        boolean result = false;
        while (!result) {
            if (!inputInfoData()) {
                return;
            }
            System.out.println();
            result = checkInfoData();
        }
        sc.close();

        System.out.println("설정 완료");
        System.out.println("");


        System.out.println("연결 시도 중입니다.");
        SocketAddress socketAddress = new InetSocketAddress(deviceIp, devicePort);
        Socket socket = new Socket();
        try {
            socket.setSoTimeout(5000);
            socket.connect(socketAddress, 5000);

            System.out.println("연결 성공");
            DataOutputStream bufferedWriter = new DataOutputStream(socket.getOutputStream());

            String dataFormat = "{\"server_addr\":\"%s\",\"server_port\":\"%d\",\"ssl_support\":\"no\",\"ssid\":\"%s\",\"pass\":\"%s\",\"mqtt_key\":\"%s\",\"company\":\"DAWONDNS\",\"model\":\"%s\",\"topic\":\"dwd\"}";
            String sendData = String.format(dataFormat, mqttIp, mqttPort, wifiName, wifiPasswd, mqttPasswd, deviceModel);
            System.out.println("SendData: " + sendData);

            (new PrintWriter(bufferedWriter, true)).println(sendData);
            System.out.println("#### 성공 ####");

        } catch (SocketException e) {
            System.out.println("#### 실패 ####");
            e.printStackTrace();
        } catch (IOException e) {
            System.out.println("#### 실패 ####");
            e.printStackTrace();
        } finally {
            try {
                socket.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    private static boolean inputInfoData() {
        System.out.println("######### [WIFI 설정] #########");
        System.out.println("WIFI 이름을 입력하세요.");
        wifiName = sc.next();
        if (wifiName == null || wifiName.length() == 0) {
            System.out.println("[오류] - WIFI 이름 미입력");
            return false;
        }

        System.out.println("WIFI 비밀번호을 입력하세요. (8자리 이상)");
        wifiPasswd = sc.next();
        if (wifiPasswd == null || wifiPasswd.length() < 8) {
            System.out.println("[오류] - WIFI 비밀번호 미입력 또는 8자리 미만");
            return false;
        }
        System.out.println("##############################");
        System.out.println();

        System.out.println("######### [MQTT 설정] #########");
        System.out.println("MQTT 서버 주소(IP or Domain)를 입력하세요");
        mqttIp = sc.next();
        if (mqttIp == null || mqttIp.length() == 0) {
            System.out.println("[오류] - MQTT 서버 주소 미입력");
            return false;
        }

        System.out.println("MQTT 서버 포트를 입력하세요. (기본값: 1883)");
        mqttPort = sc.nextInt();
        if (mqttPort == 0) {
            mqttPort = 1883;
        }
        if (mqttPort <= 0 || mqttPort > 65535) {
            System.out.println("[오류] - MQTT 서버 포트 미입력 또는 포트 가용 범위가 아님.");
            return false;
        }
        System.out.println("MQTT 서버 비밀번호를 입력하세요. (1234 입력 권장)");
        mqttPasswd = sc.next();

        System.out.println("##############################");
        System.out.println();

        System.out.println("#### [디바이스(스마트 플러그) 설정] ###");
        System.out.println("디바이스 모델명를 입력하세요. (기본값: B540-WF) 지원 모델: B530-WF/B540-WF/B400-W");
        deviceModelName = sc.next();
        if (deviceModelName == null || deviceModelName.length() == 0) {
            deviceModelName = "B540-WF";
        }
        if (deviceModelName.equalsIgnoreCase("B540-WF") || deviceModelName.equalsIgnoreCase("B530-WF")) {
            deviceModel = "B5X";
        } else if (deviceModelName.equalsIgnoreCase("B400-W")) {
            deviceModel = "B400_SW";
        } else {
            System.out.println("[오류] - 지원하지 않는 디바이스 모델 입니다.");
            return false;
        }

        System.out.println("디바이스 주소(IP)를 입력하세요. (IPv4) (기본값: " + deviceIp + ")");
        deviceIp = sc.next();
        if (deviceIp == null || deviceIp.length() == 0) {
            deviceIp = "192.168.43.1";
        }
        if (!isValidInet4Address(deviceIp)) {
            System.out.println("[오류] - 디바이스 주소 미입력 또는 IPv4 형식이 아님");
            return false;
        }

        System.out.println("디바이스 포트를 입력하세요. (기본값: 5000)");
        devicePort = sc.nextInt();
        if (devicePort == 0) {
            devicePort = 5000;
        }
        if (devicePort <= 0 || devicePort > 65535) {
            System.out.println("[오류] - 디바이스 포트 미입력 또는 포트 가용 범위가 아님.");
            return false;
        }
        return true;
    }

    private static boolean checkInfoData() {
        System.out.println("########## [설정 확인] #########");
        System.out.println(String.format("WIFI 이름: %s", wifiName));
        System.out.println(String.format("WIFI 비밀번호: %s", wifiPasswd));
        System.out.println(String.format("MQTT IP: %s", mqttIp));
        System.out.println(String.format("MQTT 포트: %d", mqttPort));
        System.out.println(String.format("MQTT 비밀번호: %s", mqttPasswd));
        System.out.println(String.format("디바이스 모델명: %s (%s)", deviceModelName, deviceModel));
        System.out.println(String.format("디바이스 IP: %s", deviceIp));
        System.out.println(String.format("디바이스 포트: %d", devicePort));
        System.out.println();

        System.out.println("위 설정이 맞습니까? (y/n)");
        String result = "";
        while (result == null || result.length() == 0 || !(result.equalsIgnoreCase("Y") || result.equalsIgnoreCase("N"))) {
            result = sc.next();
        }
        return result.equalsIgnoreCase("Y");
    }

    public static boolean isValidInet4Address(String inet4Address) {
        if (inet4Address == null || inet4Address.length() == 0) {
            return false;
        }
        String[] groups = inet4Address.split("\\.");
        if (groups.length != 4) {
            return false;
        }

        // verify that address subgroups are legal
        for (String ipSegment : groups) {
            if (ipSegment == null || ipSegment.length() == 0) {
                return false;
            }
            int iIpSegment = 0;
            try {
                iIpSegment = Integer.parseInt(ipSegment);
            } catch (NumberFormatException e) {
                return false;
            }
            if (iIpSegment > 255) {
                return false;
            }
            if (ipSegment.length() > 1 && ipSegment.startsWith("0")) {
                return false;
            }
        }
        return true;
    }
}
