import datetime
import logging
from dataclasses import dataclass
from typing import Any, Optional, List

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .client.dh_lottery_client import DhLotteryError, DhLotteryClient, \
    DhLotteryBalanceData
from .client.dh_lotto_645 import DhLotto645
from .const import COORDINATOR_UPDATE_INTERVAL, LOTTERY_UPDATE_INTERVAL, LOTTO_645_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class DhLotto645BuyData:
    """로또 구매 내역을 나타내는 데이터 클래스입니다."""
    round_no: int
    barcode: str
    game: DhLotto645.Game
    result: str
    rank: int = None


class DhCoordinator(DataUpdateCoordinator):
    """동행복권 데이터 업데이트 코디네이터입니다."""
    client: DhLotteryClient


class DhLotteryCoordinator(DhCoordinator):
    """동행복권 데이터 업데이트 코디네이터입니다."""

    def __init__(self, hass: HomeAssistant, client: DhLotteryClient):
        super().__init__(
            hass,
            _LOGGER,
            name="DhLotteryCoordinator",
            update_interval=COORDINATOR_UPDATE_INTERVAL,
        )
        self.client = client
        self._balance_last_updated: Optional[datetime.datetime] = None

    async def _async_update_data(self) -> dict[str, Any]:
        """동행복권 데이터를 비동기로 업데이트합니다."""
        try:
            balance: Optional[DhLotteryBalanceData] = None
            if self._async_check_update_balance():
                async with async_timeout.timeout(10):
                    balance = await self.client.async_get_balance()
                    self._balance_last_updated = datetime.datetime.now()

            return {
                "balance": balance
            }
        # except DhLotteryLoginError as err:
        # Raising ConfigEntryAuthFailed will cancel future updates
        # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        # raise ConfigEntryAuthFailed from err
        except DhLotteryError as err:
            raise UpdateFailed(f"API와의 통신 오류: {err}")

    async def async_clear_refresh(self):
        """데이터를 새로고침합니다."""
        self._balance_last_updated = None
        await self.async_request_refresh()

    def _async_check_update_balance(self) -> bool:
        """예치금 정보를 업데이트할지 확인합니다."""
        if not self._balance_last_updated:
            return True
        return (datetime.datetime.now() - self._balance_last_updated) >= LOTTERY_UPDATE_INTERVAL


class DhLotto645Coordinator(DhCoordinator):
    """로또 6/45 데이터 업데이트 코디네이터입니다."""

    def __init__(self, hass: HomeAssistant, client: DhLotteryClient):

        super().__init__(
            hass,
            _LOGGER,
            name="DhLotto645Coordinator",
            update_interval=COORDINATOR_UPDATE_INTERVAL,
        )
        self.client = client
        self.lotto_645 = DhLotto645(client)
        self._latest_winning_numbers: Optional[DhLotto645.WinningData] = None
        self._buy_history_last_updated: Optional[datetime.datetime] = None
        self.winning_dict: dict[int, DhLotto645.WinningData] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Lotto 6/45 데이터를 비동기로 업데이트합니다."""
        try:
            latest_winning_numbers: Optional[DhLotto645.WinningData] = None
            if await self._async_check_update_winning_numbers():
                async with async_timeout.timeout(10):
                    latest_round_no = await self.lotto_645.async_get_latest_round_no()
                    latest_winning_numbers = await self._async_get_winning_numbers(latest_round_no)
                    self._latest_winning_numbers = latest_winning_numbers

            buy_history_this_week: List[DhLotto645BuyData] = []
            if self._async_check_update_buy_history():
                async with async_timeout.timeout(10):
                    buy_history_this_week = await self._async_get_buy_history_this_week()
                    self._buy_history_last_updated = datetime.datetime.now()
            return {
                "latest_winning_numbers": latest_winning_numbers,
                "buy_history_this_week": buy_history_this_week,
            }
        # except DhLotteryLoginError as err:
        # Raising ConfigEntryAuthFailed will cancel future updates
        # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        # raise ConfigEntryAuthFailed from err
        except DhLotteryError as err:
            raise UpdateFailed(f"API와의 통신 오류: {err}") from err

    async def async_clear_refresh(self):
        """데이터를 새로고침합니다."""
        self._latest_winning_numbers = None
        self._buy_history_last_updated = None
        self.winning_dict = {}
        await self.async_request_refresh()

    async def _async_check_update_winning_numbers(self) -> bool:
        """당첨 번호를 업데이트할지 확인합니다."""
        if not self._latest_winning_numbers:
            return True
        now = datetime.datetime.now()
        # 현재 시각이 토요일 20:40 ~ 21:30 사이인지 확인합니다.
        if now.weekday() == 5 and datetime.time(20, 40) <= now.time() <= datetime.time(21, 30):
            if now.strftime("%Y-%m-%d") != self._latest_winning_numbers.draw_date:
                return True
        return False

    def _async_check_update_buy_history(self) -> bool:
        """구매 내역을 업데이트할지 확인합니다."""
        if not self._buy_history_last_updated:
            return True
        return (datetime.datetime.now() - self._buy_history_last_updated) >= LOTTO_645_UPDATE_INTERVAL

    async def _async_get_buy_history_this_week(self) -> List[DhLotto645BuyData]:
        """이번 주의 구매 내역을 가져옵니다."""

        def calculate_rank(my_numbers: List[int], win_numbers: List[int], bonus: int) -> int:
            """로또 등수를 계산합니다."""
            same_cnt = 0  # 일치하는 개수

            for num in win_numbers:  # 각 당첨 번호 포함 여부 체크
                if num in my_numbers:
                    same_cnt += 1
            # 등수 반환
            if same_cnt == 6:
                return 1
            if same_cnt == 5 and bonus in my_numbers:
                return 2
            if same_cnt == 5:
                return 3
            if same_cnt == 4:
                return 4
            if same_cnt == 3:
                return 5
            else:
                return 6  # 꽝

        async def async_get_rank(_result: str, _numbers: List[int]) -> int:
            """등수를 비동기로 가져옵니다."""
            if _result == "미추첨":
                return -1
            if '당첨' in _result:
                winning_numbers = await self._async_get_winning_numbers(item.round_no)
                return calculate_rank(_numbers, winning_numbers.numbers, winning_numbers.bonus_num)
            return 0

        items: List[DhLotto645BuyData] = []
        for item in await self.lotto_645.async_get_buy_history_this_week():
            for game in item.games:
                items.append(DhLotto645BuyData(
                    round_no=item.round_no,
                    barcode=item.barcode,
                    game=game,
                    rank=await async_get_rank(item.result, game.numbers),
                    result=item.result,
                ))
                if len(items) >= 5:
                    break
        return items

    async def _async_get_winning_numbers(self, round_no: int):
        """당첨 번호를 비동기로 가져옵니다."""
        winning_data = self.winning_dict.get(round_no)
        if not winning_data:
            winning_data = await self.lotto_645.async_get_winning_numbers(round_no)
            self.winning_dict[round_no] = winning_data
        return winning_data
