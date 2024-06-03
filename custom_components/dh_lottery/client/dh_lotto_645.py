import datetime
import json
import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import List, Dict

from bs4 import BeautifulSoup

from .dh_lottery_client import DhLotteryClient, DH_LOTTERY_URL, DhLotteryError

_LOGGER = logging.getLogger(__name__)


class DhLotto645Error(DhLotteryError):
    """DH Lotto 645 예외 클래스입니다."""


class DhLotto645SelMode(StrEnum):
    """로또 구매 모드를 나타내는 열거형입니다."""

    AUTO = "자동"
    MANUAL = "수동"
    SEMI_AUTO = "반자동"

    @staticmethod
    def value_of(value: str) -> "DhLotto645SelMode":
        """로또 구매 모드 값을 가져옵니다."""
        if value == "1":
            return DhLotto645SelMode.MANUAL
        if value == "2":
            return DhLotto645SelMode.SEMI_AUTO
        if value == "3":
            return DhLotto645SelMode.AUTO
        raise ValueError(f"Invalid value: {value}")

    def to_value(self) -> str:
        """로또 구매 모드 값을 가져옵니다."""
        if self == DhLotto645SelMode.AUTO:
            return "0"
        if self == DhLotto645SelMode.MANUAL:
            return "1"
        if self == DhLotto645SelMode.SEMI_AUTO:
            return "2"
        raise ValueError(f"Invalid value: {self}")

    @staticmethod
    def value_of_text(text: str) -> "DhLotto645SelMode":
        """로또 구매 모드 값을 가져옵니다."""
        if "반자동" in text:
            return DhLotto645SelMode.SEMI_AUTO
        if "자동" in text:
            return DhLotto645SelMode.AUTO
        if "수동" in text:
            return DhLotto645SelMode.MANUAL
        raise ValueError(f"Invalid text: {text}")

    def __str__(self):
        """로또 구매 모드 값을 가져옵니다."""
        if self == DhLotto645SelMode.AUTO:
            return "자동"
        if self == DhLotto645SelMode.MANUAL:
            return "수동"
        if self == DhLotto645SelMode.SEMI_AUTO:
            return "반자동"
        raise ValueError(f"Invalid value: {self}")


class DhLotto645:
    """동행복권 로또 6/45를 구매하는 클래스입니다."""

    @dataclass
    class WinningData:
        """로또 당첨 정보를 나타내는 데이터 클래스입니다."""

        round_no: int
        numbers: List[int]
        bonus_num: int
        draw_date: str

    @dataclass
    class Slot:
        """로또 슬롯 정보를 나타내는 데이터 클래스입니다."""

        mode: DhLotto645SelMode = DhLotto645SelMode.AUTO
        numbers: List[int] = field(default_factory=lambda: [])

    @dataclass
    class Game:
        """로또 게임 정보를 나타내는 데이터 클래스입니다."""

        slot: str
        mode: DhLotto645SelMode = DhLotto645SelMode.AUTO
        numbers: List[int] = field(default_factory=lambda: [])

    @dataclass
    class BuyData:
        """로또 구매 결과를 나타내는 데이터 클래스입니다."""

        round_no: int
        barcode: str
        issue_dt: str
        games: List["DhLotto645.Game"] = field(default_factory=lambda: [])

        def to_dict(self) -> Dict:
            """데이터를 사전 형식으로 변환합니다."""
            return {
                "round_no": self.round_no,
                "barcode": self.barcode,
                "issue_dt": self.issue_dt,
                "games": [game.__dict__ for game in self.games],
            }

    @dataclass
    class BuyHistoryData:
        """로또 구매 내역을 나타내는 데이터 클래스입니다."""

        round_no: int
        barcode: str
        result: str
        games: List["DhLotto645.Game"] = field(default_factory=lambda: [])

    def __init__(self, client: DhLotteryClient):
        """DhLotto645 클래스를 초기화합니다."""
        self.client = client

    async def async_get_latest_round_no(self) -> int:
        """최신 로또 회차 번호를 가져옵니다."""
        resp = await self.client.session.get(f"{DH_LOTTERY_URL}/common.do?method=main")
        soup = BeautifulSoup(await resp.text(), "html5lib")
        drw_no = soup.find("strong", {"id": "lottoDrwNo"})
        if not drw_no:
            raise DhLotto645Error("최신 회차 정보를 가져올 수 없습니다.")
        return int(drw_no.text)

    async def async_get_winning_numbers(self, round_no: int) -> WinningData:
        """특정 회차의 로또 당첨 번호를 가져옵니다."""
        resp = await self.client.session.get(
            f"{DH_LOTTERY_URL}/common.do?method=getLottoNumber&drwNo={round_no}"
        )
        res_json = await resp.json(content_type="text/html")
        if res_json.get("returnValue") != "success":
            raise DhLotto645Error(f"당첨번호 조회에 실패했습니다. (회차: {round_no})")

        return DhLotto645.WinningData(
            round_no=res_json.get("drwNo"),
            numbers=[
                res_json.get("drwtNo1"),
                res_json.get("drwtNo2"),
                res_json.get("drwtNo3"),
                res_json.get("drwtNo4"),
                res_json.get("drwtNo5"),
                res_json.get("drwtNo6"),
            ],
            bonus_num=res_json.get("bnusNo"),
            draw_date=res_json.get("drwNoDate"),
        )

    async def async_buy(self, items: List[Slot]) -> BuyData:
        """
        로또를 구매합니다.
        example: {"loginYn":"Y","result":{"oltInetUserId":"006094875","issueTime":"17:55:27","issueDay":"2024/05/28",
        "resultCode":"100","barCode4":"63917","barCode5":"56431","barCode6":"42167","barCode1":"59865","barCode2":"36399",
        "resultMsg":"SUCCESS","barCode3":"04155","buyRound":"1122","arrGameChoiceNum":["A|09|12|30|33|35|433"],
        "weekDay":"화","payLimitDate":null,"drawDate":null,"nBuyAmount":1000}}
        """

        _LOGGER.debug(f"Buy Lotto, items: {items}")

        def deduplicate_numbers(_items: List["DhLotto645.Slot"]) -> None:
            """구매 번호에서 중복을 제거합니다."""
            for _item in _items:
                _item.numbers = list(set(_item.numbers))

        async def _verify_and_get_buy_count(_items: List["DhLotto645.Slot"]) -> int:
            """구매 가능한지 검증하고, 구매 가능한 로또 개수를 반환합니다."""

            def _check_buy_time() -> None:
                """구매 가능한 시간인지 확인합니다."""
                _now = datetime.datetime.now()
                if _now.hour < 6:
                    raise DhLotto645Error(
                        "❗구매 가능 시간이 아닙니다. (매일 6시부터 24시까지 구매 가능)"
                    )
                if _now.weekday() == 5 and _now.hour > 20:
                    raise DhLotto645Error(
                        "❗구매 가능 시간이 아닙니다. (추첨일 오후 8시부터 다음날(일요일) 오전 6시까지는 판매 정지)"
                    )

            def _check_item_count() -> None:
                """구매 정보 항목의 개수를 확인합니다."""
                if len(_items) == 0:
                    raise DhLotto645Error("❗구매할 로또 번호를 지정해 주세요.")
                if len(_items) > 5:
                    raise DhLotto645Error("❗구매할 게임이 5개를 초과했습니다.")
                for _idx, _item in enumerate(_items):
                    if _item.mode == DhLotto645SelMode.MANUAL and len(_item.numbers) > 6:
                        raise DhLotto645Error(
                            f"❗{_idx + 1}번째 게임의 수동 선택 번호가 6개를 초과했습니다."
                        )

            async def _async_check_weekly_limit() -> int:
                """주간 구매 제한을 확인합니다."""
                _history_items = await self.async_get_buy_history_this_week()
                __this_week_buy_count = sum(
                    [len(_item.games) for _item in _history_items if _item.result == "미추첨"]
                )
                if __this_week_buy_count >= 5:
                    raise DhLotto645Error("❗구매 가능한 게임 5회를 초과했습니다.")
                return __this_week_buy_count

            async def _async_check_balance() -> None:
                """예치금이 충분한지 확인합니다."""
                if _buy_count * 1000 > _balance.purchase_available:
                    raise DhLotto645Error(f"❗예치금이 부족합니다. (예치금: {_balance.purchase_available}원)")
                _LOGGER.debug(
                    f"Buy count: {_buy_count}, deposit: {_buy_count * 1000}/{_balance.purchase_available}원"
                )

            _check_buy_time()
            _check_item_count()
            _this_week_buy_count = await _async_check_weekly_limit()
            _available_count = 5 - _this_week_buy_count
            _LOGGER.debug(f"Available count: {_available_count}")

            _balance = await self.client.async_get_balance()
            _buy_count = min(len(items), _available_count)
            await _async_check_balance()
            return _buy_count

        async def get_user_ready_socket() -> str:
            """유저 준비 소켓을 가져옵니다."""
            _resp = await self.client.session.post(
                url="https://ol.dhlottery.co.kr/olotto/game/egovUserReadySocket.json"
            )
            return json.loads(await _resp.text())["ready_ip"]

        def make_param(tickets: List["DhLotto645.Slot"]) -> str:
            """로또 구매 정보를 생성합니다."""
            return json.dumps(
                [
                    {
                        "genType": (
                            DhLotto645SelMode.SEMI_AUTO
                            if t.mode == DhLotto645SelMode.MANUAL
                               and len(t.numbers) != 6
                            else t.mode
                        ).to_value(),
                        "arrGameChoiceNum": (
                            None
                            if t.mode == DhLotto645SelMode.AUTO
                            else ",".join(map(str, sorted(t.numbers)))
                        ),
                        "alpabet": "ABCDE"[i],
                    }
                    for i, t in enumerate(tickets)
                ]
            )

        def parse_result(result: Dict) -> DhLotto645.BuyData:
            """구매 결과를 파싱합니다.
            example: ["A|01|02|04|27|39|443", "B|11|23|25|27|28|452"]
            """
            return DhLotto645.BuyData(
                round_no=int(result["buyRound"]),
                issue_dt=f'{result["issueDay"]} {result["weekDay"]} {result["issueTime"]}',
                barcode=f'{result["barCode1"]} {result["barCode2"]} {result["barCode3"]} '
                        f'{result["barCode4"]} {result["barCode5"]} {result["barCode6"]}',
                games=[
                    DhLotto645.Game(
                        slot=_item[0],
                        mode=DhLotto645SelMode.value_of(_item[-1]),
                        numbers=[int(x) for x in _item[2:-1].split("|")],
                    )
                    for _item in result["arrGameChoiceNum"]
                ],
            )

        try:
            deduplicate_numbers(items)
            buy_count = await _verify_and_get_buy_count(items)
            buy_items = items[:buy_count]
            resp = await self.client.session.post(
                url="https://ol.dhlottery.co.kr/olotto/game/execBuy.do",
                data={
                    "round": str(await self.async_get_latest_round_no() + 1),
                    "direct": (await get_user_ready_socket()),
                    "nBuyAmount": str(1000 * len(buy_items)),
                    "param": make_param(buy_items),
                    "gameCnt": len(buy_items),
                },
                timeout=10,
            )
            response = await resp.json()
            if response["result"]["resultCode"] != "100":
                raise DhLotto645Error(
                    f"❗로또6/45 구매에 실패했습니다. (사유: {response['result']['resultMsg']})"
                )
            return parse_result(response["result"])
        except DhLotteryError:
            raise
        except Exception as ex:
            raise DhLotto645Error(f"❗로또6/45 구매에 실패했습니다. (사유: {str(ex)})") from ex

    async def async_get_buy_history_this_week(self) -> list[BuyHistoryData]:
        """최근 1주일간의 구매 내역을 조회합니다."""
        pattern = r"detailPop\('(\d+)', '(\d+)'"

        async def async_get_receipt(_order_no: str, _barcode: str) -> List[DhLotto645.Game]:
            """영수증을 가져옵니다."""
            _resp = await self.client.session.get(
                f"{DH_LOTTERY_URL}/myPage.do?method=lotto645Detail&orderNo={_order_no}&barcode={_barcode}&issueNo=1"
            )
            _soup = BeautifulSoup(await _resp.text(), "html5lib")
            _slots: List[DhLotto645.Game] = []
            for li in _soup.select("div.selected ul li"):
                title = li.select("strong span")
                nums = li.select("div.nums span span")
                _slots.append(
                    DhLotto645.Game(
                        slot=title[0].text.strip(),
                        mode=DhLotto645SelMode.value_of_text(title[1].text.strip()),
                        numbers=[int(num.text.strip()) for num in nums],
                    )
                )
            return _slots

        try:
            trs = await self.client.async_get_buy_list("LO40")
            items: List[DhLotto645.BuyHistoryData] = []
            for tr in trs:
                receipt_link = tr.select("td")[3].select("a")
                if not receipt_link:
                    continue
                href = receipt_link[0]["href"]
                matches = re.search(pattern, href)
                if not matches:
                    continue
                order_no = matches.group(1)
                barcode = matches.group(2)
                items.append(
                    DhLotto645.BuyHistoryData(
                        round_no=int(tr.select("td")[2].text.strip()),
                        barcode=tr.select("td")[3].text.strip(),
                        result=tr.select("td")[5].text.strip(),
                        games=await async_get_receipt(order_no, barcode),
                    )
                )
                if sum([len(item.games) for item in items]) >= 5:
                    break
            return items
        except Exception as ex:
            raise DhLotteryError("❗최근 1주일간의 구매내역을 조회하지 못했습니다.") from ex
