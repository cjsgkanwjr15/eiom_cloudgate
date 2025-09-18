import re, requests
from datetime import datetime, timedelta, timezone
import json

from ..ai_client import BaseAIClient
from ..db_client import MysqlClient


class SolticeClient:
    def __init__(self, db_client: MysqlClient, ai_client: BaseAIClient):
        """
        SolticeClient 초기화

        Args:
            db_client (MysqlClient): MySQL 데이터베이스 클라이언트
            ai_client (BaseAIClient): AI 클라이언트

        Attributes:
            db_client (MysqlClient): 데이터베이스 연결 및 토큰 관리
            ai_client (BaseAIClient): AI 기능 제공
            mall_id (str): 쇼핑몰 ID ("casa999")
        """
        self.db_client = db_client
        self.ai_client = ai_client
        self.mall_id = "ssgbio"

    def get_order_id(self, buyer_cellphone):
        print(buyer_cellphone)
        access_token = self.db_client.get_cafe24_access_token()
        end_date_raw = datetime.now()
        end_date = end_date_raw.strftime("%Y-%m-%d")
        start_date_raw = datetime.now() - timedelta(days=90)
        start_date = start_date_raw.strftime("%Y-%m-%d")
        base_url = f"https://{self.mall_id}.cafe24api.com"
        url = f"{base_url}/api/v2/admin/orders"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        params = {
            "start_date": start_date,
            "buyer_cellphone": buyer_cellphone,
            "end_date": end_date,
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        orders = data.get("orders", [])

        # 모든 주문의 order_id를 리스트로 추출
        order_ids = [o.get("order_id") for o in orders if "order_id" in o]
        return order_ids

    def get_order_info(self, order_id):

        end_date_raw = datetime.now()
        end_date = end_date_raw.strftime("%Y-%m-%d")
        start_date_raw = datetime.now() - timedelta(days=90)
        start_date = start_date_raw.strftime("%Y-%m-%d")
        base_url = f"https://{self.mall_id}.cafe24api.com"
        url = f"{base_url}/api/v2/admin/orders/{order_id}"

        headers = {
            "Authorization": f"Bearer {self.db_client.get_cafe24_access_token()}",
            "Content-Type": "application/json",
        }
        params = {
            "start_date": start_date,
            "order_id": order_id,
            "end_date": end_date,
        }

        response = requests.get(url, headers=headers, params=params)

        data = response.json()
        print("-----data--------")
        print(data)
        print("\n")
        order = data.get("order", {})
        order_date = order.get("order_date")
        payment_method = order.get("payment_method")
        paid = order.get("paid")
        canceled = order.get("canceled")

        order_info = []

        items = self.get_order_items_info(order_id)
        for item in items:
            product_name = item.get("product_name")
            option_value = item.get("option_value")
            quantity = item.get("quantity")
            tracking_no = item.get("tracking_no")
            shipping_company = item.get("shipping_company_name", None)
            delivered_date = None
            status_text = item.get("status_text")

            if tracking_no:
                if shipping_company == "CJ대한통운":
                    status_text, date = self.get_cj_logistics_delivery_data(tracking_no)
                    print(date)
                    if status_text == "배송완료":
                        delivered_date = date

            order_info.append(
                {
                    "주문 일자": order_date,
                    "제품명": product_name,
                    "옵션": option_value,
                    "수량": quantity,
                    "배송 상태": status_text,
                    "배송 완료 일자": delivered_date,
                    "송장번호": tracking_no,
                    "결제 수단": payment_method,
                    "결제 여부": paid,
                    "취소 여부": canceled,
                }
            )
        return order_info

    def get_order_items_info(self, order_id):
        """
        주문 ID로 주문 아이템의 기본 정보를 조회합니다.

        Args:
            order_id (str): 조회할 주문 번호

        Returns:
            list: 주문 아이템 리스트. 각 아이템은 다음 키를 포함:
                - product_name (str): 상품 이름
                - quantity (str): 주문 수량

        Note:
            주문의 기본 아이템 정보(상품명, 수량)만 조회합니다.
            배송 정보나 기타 상세 정보는 포함되지 않습니다.
        """
        access_token = self.db_client.get_cafe24_access_token()
        base_url = f"https://{self.mall_id}.cafe24api.com"
        url = f"{base_url}/api/v2/admin/orders/{order_id}/items"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)

        data = response.json()
        items = data.get("items", [])
        print("---items----")
        print(items)

        result = [
            {
                "option_value": re.sub(
                    r"^.*?\]", "", item.get("option_value", "")
                ).strip(),
                "quantity": item.get("quantity"),
                "tracking_no": item.get("tracking_no"),
                "shipping_company_name": item.get("shipping_company_name"),
                "status_text": item.get("status_text"),
                "product_name": item.get("product_name"),
            }
            for item in items
        ]

        return result

    def get_cj_logistics_delivery_data(self, slip_no):
        # 1. 세션 생성 및 쿠키(JSESSIONID) 획득
        info_url = "https://trace.cjlogistics.com/web/detail.jsp"
        session = requests.Session()
        session.get(info_url)
        jsessionid = session.cookies.get("JSESSIONID", None)

        if not jsessionid:
            # 쿠키가 없다면, 상황에 맞춰 예외처리를 해 주세요.
            raise ValueError("JSESSIONID 쿠키를 가져오지 못했습니다.")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }
        cookies = {"JSESSIONID": jsessionid}

        # 2. 조회할 API URL 및 요청 설정
        api_url = "https://trace.cjlogistics.com/web/rest/selectScanInfo.do"
        data = {"slipno": slip_no}  # 매개변수로 받은 운송장 번호

        try:
            # 3. POST 요청 실행
            response = requests.post(
                api_url, headers=headers, cookies=cookies, data=data
            )
            response.raise_for_status()  # 요청 실패 시 에러가 발생하도록 설정
            # 4. JSON 응답 파싱
            response_json = response.json()
            # "scanInfoOutput" 리스트가 존재하고, 최소 1개 이상의 데이터가 있다고 가정
            scan_info_list = response_json.get("data", {}).get("scanInfoOutput", [])

            if not scan_info_list:
                # 리스트가 비었을 때의 처리 (무언가를 반환하거나 예외 처리)
                return "배송 정보 없음", "현재 위치 알 수 없음"
            latest_scan = scan_info_list[0]
            print({"latest_scan": latest_scan})
            delivery_status = latest_scan.get("basisSclsfCdNm")  # 배송 상태명
            date = latest_scan.get("scanDt")  # 스캔날짜
            return delivery_status, date
        except Exception as e:
            print("배송 조회를 실패했습니다: ", e)
            return "배송 조회를 실패했으므로 담당자를 연결해야합니다."

    def cancel_card_order(self, order_id, reason_type, reason):
        cafe24_access_token = self.db_client.get_cafe24_access_token()
        print("cafe24_access_token: ", cafe24_access_token)
        url = f"https://{self.mall_id}.cafe24api.com/api/v2/admin/cancellationrequests"
        payload = {
            "shop_no": 1,
            "requests": [
                {
                    "order_id": f"{order_id}",
                    "reason_type": f"{reason_type}",
                    "reason": f"{reason}",
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {cafe24_access_token}",
            "Content-Type": "application/json",
            # "X-Cafe24-Api-Version": "{version}",
        }
        try:
            response = requests.request("POST", url, json=payload, headers=headers)
            print(response.text)
            return "카드 주문취소가 완료되었습니다."
        except Exception as e:
            print("카드 주문취소에 실패했습니다.")
            return "카드 주문취소에 실패했으므로 담당자를 연결해야합니다."

    def cancel_cash_order(
        self,
        order_id,
        reason_type,
        reason,
        refund_bank_code,
        refund_bank_account_no,
        refund_bank_account_holder,
    ):
        cafe24_access_token = self.db_client.get_cafe24_access_token()
        print("cafe24_access_token: ", cafe24_access_token)
        url = f"https://{self.mall_id}.cafe24api.com/api/v2/admin/cancellationrequests"
        payload = {
            "shop_no": 1,
            "requests": [
                {
                    "order_id": f"{order_id}",
                    "reason_type": f"{reason_type}",
                    "reason": f"{reason}",
                    "refund_bank_code": f"{refund_bank_code}",
                    "refund_bank_account_no": f"{refund_bank_account_no}",
                    "refund_bank_account_holder": f"{refund_bank_account_holder}",
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {cafe24_access_token}",
            "Content-Type": "application/json",
            # "X-Cafe24-Api-Version": "{version}",
        }
        try:
            response = requests.request("POST", url, json=payload, headers=headers)
            print(response.text)
            return "무통장입금 주문취소가 완료되었습니다."
        except Exception as e:
            print("무통장입금 주문 취소 실패")
            return "무통장입금 주문 취소 실패하였으므로 담당자 연결해야합니다."
