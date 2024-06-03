import datetime
import logging
import threading
from dataclasses import dataclass

import aiohttp
from bs4 import BeautifulSoup, Tag

_LOGGER = logging.getLogger(__name__)

DH_LOTTERY_URL = "https://dhlottery.co.kr"


@dataclass
class DhLotteryBalanceData:
    deposit: int = 0  # 총예치금
    purchase_available: int = 0  # 구매가능금액
    reservation_purchase: int = 0  # 예약구매금액
    withdrawal_request: int = 0  # 출금신청중금액
    purchase_impossible: int = 0  # 구매불가능금액
    this_month_accumulated_purchase: int = 0  # 이번달누적구매금액


class DhLotteryError(Exception):
    """DH Lottery 예외 클래스입니다."""


class DhLotteryLoginError(DhLotteryError):
    """로그인에 실패했을 때 발생하는 예외입니다."""


class DhLotteryClient:

    def __init__(self, username: str, password: str):
        """DhLotteryClient 클래스를 초기화합니다."""
        self.username = username
        self._password = password
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/91.0.4472.77 Safari/537.36",
                "Connection": "keep-alive",
                "Cache-Control": "max-age=0",
                "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
                "sec-ch-ua-mobile": "?0",
                "Upgrade-Insecure-Requests": "1",
                "Origin": DH_LOTTERY_URL,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,"
                          "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Referer": DH_LOTTERY_URL,
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ko-KR;q=0.7",
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        self.lock = threading.RLock()
        self.logged_in = False

    async def async_get_with_login(
            self,
            path: str,
            retry: int = 1,
    ) -> BeautifulSoup:
        """로그인이 필요한 페이지를 가져옵니다."""
        with self.lock:
            try:
                resp = await self.session.get(url=f"{DH_LOTTERY_URL}/{path}")
                soup = BeautifulSoup(await resp.text(), "html5lib")
                if not soup.find("a", {"class": "btn_common"}, string="로그아웃"):
                    _LOGGER.debug("required login. retry: %d", retry)
                    if retry > 0:
                        await self.async_login()
                        return await self.async_get_with_login(path, retry - 1)
                    raise DhLotteryLoginError(
                        "❗로그인에 실패했습니다. 세션 상태를 확인해주세요."
                    )
                return soup
            except DhLotteryError:
                raise
            except Exception as ex:
                raise DhLotteryError(
                    "❗로그인이 필요한 페이지를 가져오지 못했습니다."
                ) from ex

    async def async_login(self):
        """로그인을 수행합니다."""
        _LOGGER.info("login")
        try:
            resp = await self.session.post(
                url=f"{DH_LOTTERY_URL}/userSsl.do?method=login",
                data={
                    "returnUrl": f"{DH_LOTTERY_URL}/common.do?method=main",
                    "userId": self.username,
                    "password": self._password,
                    "checkSave": "off",
                    "newsEventYn": "",
                },
            )
            soup = BeautifulSoup(await resp.text(), "html5lib")
            if soup.find("a", attrs={"class": "btn_common"}):
                self.logged_in = False
                raise DhLotteryLoginError(
                    "로그인에 실패했습니다. 아이디 또는 비밀번호를 확인해주세요. (5회 실패했을 수도 있습니다. 이 경우엔 홈페이지에서 비밀번호를 변경해야 합니다)"
                )
            self.logged_in = True
        except DhLotteryError:
            raise
        except Exception as ex:
            raise DhLotteryError("❗로그인을 수행하지 못했습니다.") from ex

    async def async_get_balance(self) -> DhLotteryBalanceData:
        """예치금 현황을 조회합니다."""
        try:
            soup = await self.async_get_with_login("userSsl.do?method=myPage")
            elem = soup.select("div.box.money")[0]

            td_ta_right = elem.select(".tbl_total_account_number tbody td.ta_right")
            # 간편충전 계좌번호가 없는 경우
            return DhLotteryBalanceData(
                deposit=self.parse_digit(
                    elem.select("p.total_new > strong")[0].text.strip()
                ),
                purchase_available=self.parse_digit(td_ta_right[0].text.strip()),
                reservation_purchase=self.parse_digit(td_ta_right[1].text.strip()),
                withdrawal_request=self.parse_digit(td_ta_right[2].text.strip()),
                purchase_impossible=self.parse_digit(td_ta_right[3].text.strip()),
                this_month_accumulated_purchase=self.parse_digit(
                    td_ta_right[4].text.strip()
                ),
            )
        except Exception as ex:
            raise DhLotteryError("❗예치금 현황을 조회하지 못했습니다.") from ex

    async def async_get_buy_list(self, lotto_id: str) -> list[Tag]:
        """1주일간의 구매내역을 조회합니다."""
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=7)
        await self.async_get_with_login("myPage.do?method=lottoBuyListView")
        try:
            resp = await self.session.post(
                f"{DH_LOTTERY_URL}/myPage.do?method=lottoBuyList",
                data={
                    "nowPage": "1",
                    "searchStartDate": start_date.strftime("%Y%m%d"),
                    "searchEndDate": end_date.strftime("%Y%m%d"),
                    "lottoId": lotto_id,
                    "winGrade": "2",
                    "calendarStartDt": start_date.strftime("%Y-%m-%d"),
                    "calendarEndDt": end_date.strftime("%Y-%m-%d"),
                    "sortOrder": "DESC",
                },
            )
            soup = BeautifulSoup(await resp.text(), "html5lib")
            if soup.find("td", {"class": "nodata"}):
                return []
            return soup.select("table.tbl_data_col tbody tr")
        except Exception as ex:
            raise DhLotteryError(
                "❗최근 1주일간의 구매내역을 조회하지 못했습니다."
            ) from ex

    @staticmethod
    def parse_digit(text) -> int:
        """문자열에서 숫자를 추출하여 정수로 변환합니다."""
        numbers = "".join([c for c in text if c.isdigit()])
        return int(numbers) if numbers else 0
