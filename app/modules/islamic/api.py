from __future__ import annotations

import calendar
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.modules.islamic.schemas import AyahValue, IslamicInputError, PrayerTimeValue

ALADHAN_BASE_URL = "https://api.aladhan.com/v1"
QURAN_BASE_URL = "https://api.alquran.cloud/v1"
QURAN_IMAGE_URL = "https://cdn.alquran.cloud/media/image/{surah}/{ayah}"
PRAYER_NAMES = {
    "Fajr": "Subuh",
    "Dhuhr": "Zuhur",
    "Asr": "Asar",
    "Maghrib": "Magrib",
    "Isha": "Isya",
}


class IslamicAPIClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def calculation_methods(self) -> list[tuple[int, str]]:
        payload = await self._json(f"{ALADHAN_BASE_URL}/methods")
        data = payload.get("data", {})
        methods: list[tuple[int, str]] = []
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, dict) and isinstance(value.get("id"), int):
                    methods.append((value["id"], str(value.get("name", value["id"]))))
        return sorted(set(methods))

    async def detect_timezone(
        self,
        *,
        latitude: float | None,
        longitude: float | None,
        city: str | None,
        country: str | None,
    ) -> str:
        params = self._location_params(latitude, longitude, city, country)
        endpoint = (
            "timingsByCity"
            if city and country
            else f"timings/{int(datetime.now(timezone.utc).timestamp())}"
        )
        payload = await self._json(f"{ALADHAN_BASE_URL}/{endpoint}", params=params)
        timezone_name = payload.get("data", {}).get("meta", {}).get("timezone")
        return self.validate_timezone(str(timezone_name or "Asia/Jakarta"))

    async def monthly_prayers(
        self,
        *,
        year: int,
        month: int,
        latitude: float | None,
        longitude: float | None,
        city: str | None,
        country: str | None,
        timezone_name: str,
        method: int | None,
    ) -> list[PrayerTimeValue]:
        params = self._location_params(latitude, longitude, city, country)
        if method is not None:
            params["method"] = method
        endpoint = "calendarByCity" if city and country else "calendar"
        payload = await self._json(
            f"{ALADHAN_BASE_URL}/{endpoint}/{year}/{month}", params=params
        )
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise IslamicInputError("Jadwal dari AlAdhan tidak valid.")
        tz = ZoneInfo(self.validate_timezone(timezone_name))
        result: list[PrayerTimeValue] = []
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            gregorian = row.get("date", {}).get("gregorian", {}).get("date")
            try:
                local_date = datetime.strptime(str(gregorian), "%d-%m-%Y").date()
            except ValueError:
                local_date = date(year, month, index)
            timings = row.get("timings", {})
            for source_name, display_name in PRAYER_NAMES.items():
                raw = str(timings.get(source_name, ""))[:5]
                try:
                    hour, minute = (int(part) for part in raw.split(":"))
                    local = datetime(
                        local_date.year,
                        local_date.month,
                        local_date.day,
                        hour,
                        minute,
                        tzinfo=tz,
                    )
                except (TypeError, ValueError):
                    raise IslamicInputError("Waktu salat dari AlAdhan tidak valid.") from None
                adhan_at = local.astimezone(timezone.utc)
                result.append(
                    PrayerTimeValue(
                        local_date=local_date,
                        prayer_name=display_name,
                        adhan_at=adhan_at,
                        quran_at=adhan_at + timedelta(minutes=random.randint(5, 20)),
                    )
                )
        expected = calendar.monthrange(year, month)[1] * len(PRAYER_NAMES)
        if len(result) != expected:
            raise IslamicInputError("Kalender AlAdhan tidak lengkap.")
        return result

    async def ayah_by_number(self, number: int) -> AyahValue:
        return self._ayah(
            (await self._json(f"{QURAN_BASE_URL}/ayah/{number}/quran-uthmani")).get("data")
        )

    async def ayah_by_reference(self, reference: str) -> AyahValue:
        return self._ayah(
            (await self._json(f"{QURAN_BASE_URL}/ayah/{reference}/quran-uthmani")).get("data")
        )

    async def page(self, page: int) -> list[AyahValue]:
        payload = await self._json(f"{QURAN_BASE_URL}/page/{page}/quran-uthmani")
        rows = payload.get("data", {}).get("ayahs")
        if not isinstance(rows, list) or not rows:
            raise IslamicInputError("Halaman Quran tidak ditemukan.")
        return [self._ayah(row) for row in rows]

    async def ayah_range(self, start: int, end: int, *, limit: int = 5) -> list[AyahValue]:
        stop = min(end, start + limit - 1)
        values = []
        for number in range(start, stop + 1):
            values.append(await self.ayah_by_number(number))
        return values

    async def download_image(self, ayah: AyahValue) -> bytes:
        try:
            response = await self._http.get(
                QURAN_IMAGE_URL.format(
                    surah=ayah.surah_number, ayah=ayah.number_in_surah
                ),
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise IslamicInputError("Gambar ayat gagal diunduh.") from error
        if not response.content:
            raise IslamicInputError("Gambar ayat kosong.")
        return response.content

    @staticmethod
    def validate_timezone(value: str) -> str:
        value = value.strip()
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise IslamicInputError("Timezone harus berupa nama IANA, misalnya Asia/Jakarta.") from error
        return value

    @staticmethod
    def _location_params(
        latitude: float | None,
        longitude: float | None,
        city: str | None,
        country: str | None,
    ) -> dict[str, Any]:
        if city and country:
            return {"city": city, "country": country}
        if latitude is None or longitude is None:
            raise IslamicInputError("Lokasi belum lengkap.")
        return {"latitude": latitude, "longitude": longitude}

    @staticmethod
    def _ayah(data: Any) -> AyahValue:
        if not isinstance(data, dict) or not isinstance(data.get("number"), int):
            raise IslamicInputError("Ayat Quran tidak ditemukan.")
        surah = data.get("surah", {})
        return AyahValue(
            number=int(data["number"]),
            surah_number=int(surah["number"]),
            surah_name=str(surah.get("englishName", surah["number"])),
            number_in_surah=int(data["numberInSurah"]),
            page=int(data["page"]),
        )

    async def _json(self, url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = await self._http.get(url, params=params, follow_redirects=True)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise IslamicInputError("Layanan data Islami sedang tidak tersedia.") from error
        if not isinstance(payload, dict) or payload.get("code", 200) != 200:
            raise IslamicInputError("Layanan data Islami menolak permintaan.")
        return payload
