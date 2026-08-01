from __future__ import annotations

import asyncio
import re
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

from app.core.telegram_client import InputFile, TelegramBotClient
from app.modules.islamic.api import IslamicAPIClient
from app.modules.islamic.schemas import AyahValue, IslamicInputError, ScopeValue
from app.modules.islamic.services import IslamicService, TOTAL_QURAN_AYAHS
from app.shared.types import TelegramCallbackQuery, TelegramUpdate, UserContext

READ_PATTERN = re.compile(r"^(\d+)([pa])$", re.IGNORECASE)
AYAH_PATTERN = re.compile(r"^(\d{1,3}):(\d{1,3})$")


class IslamicRouter:
    def __init__(
        self,
        service: IslamicService,
        api: IslamicAPIClient,
        telegram: TelegramBotClient,
    ) -> None:
        self._service = service
        self._api = api
        self._telegram = telegram

    async def dispatch(self, update: TelegramUpdate, context: UserContext) -> None:
        if update.callback_query is not None:
            await self._handle_callback(update.callback_query, context)
            return
        message = update.message
        if message is None:
            return
        scope = await self._service.ensure_scope(
            chat_id=context.chat_id, chat_type=context.chat_type
        )
        try:
            if message.location is not None:
                await self._handle_location(scope, message.location.latitude, message.location.longitude)
                return
            text = (message.text or "").strip()
            if not text:
                return
            command, arguments = self._command(text)
            if command is not None:
                if not self._is_for_this_bot(command):
                    return
                command = command.split("@", 1)[0].lower()
                if command in ("/start", "/help"):
                    await self._send(context.chat_id, self._help_text())
                elif command == "/setup":
                    await self._start_setup(scope)
                elif command == "/quran":
                    await self._start_quran(scope)
                elif command == "/read":
                    await self._start_read(scope, arguments)
                elif command == "/stats":
                    await self._send_stats(scope)
                else:
                    await self._send(context.chat_id, "Command tidak dikenali. Gunakan /help.")
                return
            await self._handle_state_text(scope, text)
        except IslamicInputError as error:
            await self._send(context.chat_id, escape(str(error)))

    def _command(self, text: str) -> tuple[str | None, str]:
        first, separator, rest = text.partition(" ")
        return (first, rest.strip()) if first.startswith("/") else (None, text)

    def _is_for_this_bot(self, command: str) -> bool:
        if "@" not in command:
            return True
        suffix = command.split("@", 1)[1]
        identity = self._telegram.identity
        return bool(identity and identity.username and suffix.lower() == identity.username.lower())

    async def _start_setup(self, scope: ScopeValue) -> None:
        await self._service.set_setup_state(scope.id, "setup_choose_location", {})
        buttons = [
            [{"text": "📍 Kirim lokasi", "callback_data": "isl:setup:location:0"}],
            [{"text": "Kota & negara", "callback_data": "isl:setup:city:0"}],
            [{"text": "Koordinat manual", "callback_data": "isl:setup:coords:0"}],
            [{"text": "Batal", "callback_data": "isl:setup:cancel:0"}],
        ]
        await self._replace_setup_message(
            scope,
            chat_id=scope.chat_id,
            text="Pilih cara menentukan lokasi jadwal adzan:",
            reply_markup={"inline_keyboard": buttons},
        )

    async def _handle_location(self, scope: ScopeValue, latitude: float, longitude: float) -> None:
        if scope.setup_state != "setup_await_location":
            raise IslamicInputError("Jalankan /setup sebelum mengirim lokasi.")
        data = {"latitude": latitude, "longitude": longitude}
        data["timezone"] = await self._service.detect_timezone(data)
        scope = await self._service.merge_setup_data(
            scope.id, state="setup_choose_method", values=data
        )
        await self._show_method_menu(scope)

    async def _handle_state_text(self, scope: ScopeValue, text: str) -> None:
        state = scope.setup_state
        if state == "setup_await_city":
            city, separator, country = text.partition(",")
            if not separator or not city.strip() or not country.strip():
                raise IslamicInputError("Gunakan format: Jakarta, Indonesia")
            data: dict[str, Any] = {"city": city.strip(), "country": country.strip()}
            data["timezone"] = await self._service.detect_timezone(data)
            scope = await self._service.merge_setup_data(
                scope.id, state="setup_choose_method", values=data
            )
            await self._show_method_menu(scope)
        elif state == "setup_await_coords":
            parts = [part.strip() for part in text.split(",")]
            if len(parts) not in (2, 3):
                raise IslamicInputError("Gunakan: -6.2, 106.8 atau -6.2, 106.8, Asia/Jakarta")
            try:
                latitude, longitude = float(parts[0]), float(parts[1])
            except ValueError as error:
                raise IslamicInputError("Latitude dan longitude harus berupa angka.") from error
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise IslamicInputError("Koordinat berada di luar rentang valid.")
            data = {"latitude": latitude, "longitude": longitude}
            data["timezone"] = (
                self._api.validate_timezone(parts[2])
                if len(parts) == 3
                else await self._service.detect_timezone(data)
            )
            scope = await self._service.merge_setup_data(
                scope.id, state="setup_choose_method", values=data
            )
            await self._show_method_menu(scope)
        elif state == "setup_await_timezone":
            timezone_name = self._api.validate_timezone(text)
            scope = await self._service.merge_setup_data(
                scope.id,
                state="setup_confirm",
                values={"timezone": timezone_name},
            )
            await self._show_setup_confirmation(scope)
        elif state == "quran_await_page":
            try:
                page = int(text)
            except ValueError as error:
                raise IslamicInputError("Nomor halaman harus berupa angka.") from error
            ayah = await self._service.resolve_page_position(page)
            await self._store_pending_progress(scope, ayah)
        elif state == "quran_await_ayah":
            if AYAH_PATTERN.fullmatch(text) is None:
                raise IslamicInputError("Gunakan format surah:ayat, misalnya 2:255.")
            ayah = await self._service.resolve_ayah_position(text)
            await self._store_pending_progress(scope, ayah)
        else:
            await self._send(scope.chat_id, "Gunakan /help untuk melihat command.")

    async def _show_method_menu(self, scope: ScopeValue) -> None:
        await self._replace_setup_message(
            scope,
            chat_id=scope.chat_id,
            text="Pilih metode kalkulasi waktu salat:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "Otomatis", "callback_data": "isl:setup:auto:0"}],
                    [{"text": "Kemenag RI", "callback_data": "isl:setup:method:20"}],
                    [{"text": "Metode lainnya", "callback_data": "isl:setup:methods:0"}],
                ]
            },
        )

    async def _show_methods_page(self, scope: ScopeValue, page: int) -> None:
        methods = await self._service.methods()
        page = max(0, page)
        size = 8
        chunk = methods[page * size : (page + 1) * size]
        if not chunk:
            raise IslamicInputError("Halaman metode tidak tersedia.")
        rows = [
            [{"text": name[:45], "callback_data": f"isl:setup:method:{method_id}"}]
            for method_id, name in chunk
        ]
        navigation = []
        if page:
            navigation.append({"text": "‹", "callback_data": f"isl:setup:methods:{page - 1}"})
        if (page + 1) * size < len(methods):
            navigation.append({"text": "›", "callback_data": f"isl:setup:methods:{page + 1}"})
        if navigation:
            rows.append(navigation)
        await self._replace_setup_message(
            scope,
            chat_id=scope.chat_id,
            text="Metode kalkulasi AlAdhan:",
            reply_markup={"inline_keyboard": rows},
        )

    async def _choose_method(self, scope: ScopeValue, method: int | None) -> None:
        scope = await self._service.merge_setup_data(
            scope.id,
            state="setup_timezone_confirm",
            values={"method": method},
        )
        timezone_name = str(scope.setup_data.get("timezone", "Asia/Jakarta"))
        await self._replace_setup_message(
            scope,
            chat_id=scope.chat_id,
            text=f"Timezone terdeteksi: <code>{escape(timezone_name)}</code>",
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "Gunakan timezone ini", "callback_data": "isl:setup:tzok:0"}],
                    [{"text": "Ubah timezone", "callback_data": "isl:setup:tzchange:0"}],
                ]
            },
        )

    async def _show_setup_confirmation(self, scope: ScopeValue) -> None:
        data = scope.setup_data
        location = (
            f"{data.get('city')}, {data.get('country')}"
            if data.get("city")
            else f"{data.get('latitude')}, {data.get('longitude')}"
        )
        method = data.get("method")
        await self._replace_setup_message(
            scope,
            chat_id=scope.chat_id,
            text=(
                "Konfirmasi setup:\n"
                f"Lokasi: <code>{escape(str(location))}</code>\n"
                f"Timezone: <code>{escape(str(data.get('timezone')))}</code>\n"
                f"Metode: <code>{'Otomatis' if method is None else method}</code>"
            ),
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "Simpan", "callback_data": "isl:setup:save:0"},
                    {"text": "Batal", "callback_data": "isl:setup:cancel:0"},
                ]]
            },
        )

    async def _start_quran(self, scope: ScopeValue) -> None:
        if not scope.configured:
            raise IslamicInputError("Jalankan /setup terlebih dahulu.")
        await self._service.set_setup_state(scope.id, "quran_choose", {})
        await self._telegram.send_message(
            chat_id=scope.chat_id,
            text="Atur ayat terakhir yang sudah selesai dibaca:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "Mulai dari Al-Fatihah", "callback_data": "isl:quran:start:0"}],
                    [{"text": "Set halaman", "callback_data": "isl:quran:page:0"}],
                    [{"text": "Set surah:ayat", "callback_data": "isl:quran:ayah:0"}],
                ]
            },
        )

    async def _store_pending_progress(self, scope: ScopeValue, ayah: AyahValue) -> None:
        scope = await self._service.set_setup_state(
            scope.id, "quran_confirm", {"ayah": ayah.as_batch_item()}
        )
        await self._show_progress_confirmation(scope, ayah)

    async def _show_progress_confirmation(
        self, scope: ScopeValue, ayah: AyahValue | None
    ) -> None:
        position = (
            "belum ada ayat yang selesai"
            if ayah is None
            else f"{ayah.surah_name} {ayah.surah_number}:{ayah.number_in_surah}, halaman {ayah.page}"
        )
        await self._telegram.send_message(
            chat_id=scope.chat_id,
            text=f"Set progress menjadi <b>{escape(position)}</b>?",
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "Ya", "callback_data": "isl:quran:save:0"},
                    {"text": "Batal", "callback_data": "isl:quran:cancel:0"},
                ]]
            },
        )

    async def _start_read(self, scope: ScopeValue, arguments: str) -> None:
        match = READ_PATTERN.fullmatch(arguments.strip())
        if match is None:
            raise IslamicInputError("Gunakan /read 1p atau /read 5a.")
        session, existed, cleanup = await self._service.create_read_session(
            scope.id, int(match.group(1)), match.group(2).lower()
        )
        await self._cleanup(scope.chat_id, cleanup)
        if existed:
            await self._telegram.send_message(
                chat_id=scope.chat_id,
                text="Masih ada sesi baca aktif.",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": "Lanjutkan", "callback_data": f"isl:session:resume:{session.id}"},
                        {"text": "Batalkan", "callback_data": f"isl:session:cancel:{session.id}"},
                    ]]
                },
            )
            return
        sent = await self._telegram.send_message(
            chat_id=scope.chat_id,
            text="Pilih mode sesi baca:",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "PC", "callback_data": f"isl:mode:pc:{session.id}"},
                    {"text": "Mobile", "callback_data": f"isl:mode:mobile:{session.id}"},
                ]]
            },
        )
        await self._service.attach_prompt(session.id, sent.message_id)

    async def _send_next_batch(self, scope: ScopeValue, session_id: int) -> None:
        ayahs = await self._service.batch_ayahs(scope.id, session_id)
        if not ayahs:
            await self._send(scope.chat_id, "Batch sesi masih aktif.")
            return
        images = await asyncio.gather(*(self._service.download_image(ayah) for ayah in ayahs))
        sent_ids: list[int] = []
        items = [ayah.as_batch_item() for ayah in ayahs]
        session = await self._service.active_session(scope.id, session_id)
        if session.mode is None:
            raise IslamicInputError("Pilih mode baca terlebih dahulu.")
        try:
            for index, (ayah, image) in enumerate(zip(ayahs, images, strict=True)):
                markup = None
                if session.mode == "pc":
                    markup = {"inline_keyboard": [[{
                        "text": "Read",
                        "callback_data": f"isl:read:{ayah.number}:{session_id}",
                    }]]}
                elif index == len(ayahs) - 1:
                    markup = {"inline_keyboard": [[{
                        "text": "Tandai batch selesai",
                        "callback_data": f"isl:batch:read:{session_id}",
                    }]]}
                sent = await self._telegram.send_photo(
                    chat_id=scope.chat_id,
                    photo=InputFile(
                        filename=f"ayah-{ayah.surah_number}-{ayah.number_in_surah}.png",
                        content=image,
                        content_type="image/png",
                    ),
                    caption=(
                        f"<b>{escape(ayah.surah_name)} "
                        f"{ayah.surah_number}:{ayah.number_in_surah}</b> · halaman {ayah.page}"
                    ),
                    parse_mode="HTML",
                    reply_markup=markup,
                )
                sent_ids.append(sent.message_id)
                items[index]["message_id"] = sent.message_id
            await self._service.store_batch(scope.id, session_id, items)
        except Exception:
            await self._cleanup(scope.chat_id, sent_ids)
            raise

    async def _send_stats(self, scope: ScopeValue) -> None:
        stats = await self._service.stats(scope.id)
        progress = stats.progress
        if progress.last_ayah_number:
            position = (
                f"{progress.last_surah_name} {progress.last_surah_number}:"
                f"{progress.last_ayah_in_surah}, halaman {progress.last_page}"
            )
        else:
            position = "Belum mulai"
        percent = progress.last_ayah_number / TOTAL_QURAN_AYAHS * 100
        scope_label = "grup" if scope.chat_type in ("group", "supergroup") else "personal"
        last_activity = (
            stats.last_activity_at.astimezone(ZoneInfo(scope.timezone)).strftime(
                "%d-%m-%Y %H:%M"
            )
            if stats.last_activity_at is not None
            else "Belum ada"
        )
        await self._send(
            scope.chat_id,
            (
                f"<b>Statistik Quran {scope_label}</b>\n"
                f"Posisi: {escape(position)} ({percent:.2f}%)\n"
                f"Hari ini: {stats.today} ayat\n"
                f"7 hari: {stats.seven_days} ayat\n"
                f"30 hari: {stats.thirty_days} ayat\n"
                f"Sesi selesai: {stats.sessions_completed}\n"
                f"Streak: {stats.current_streak} hari\n"
                f"Streak terpanjang: {stats.longest_streak} hari\n"
                f"Aktivitas terakhir: {last_activity}"
            ),
        )

    async def _handle_callback(
        self, callback: TelegramCallbackQuery, context: UserContext
    ) -> None:
        data = callback.data or ""
        parts = data.split(":")
        if len(parts) != 4 or parts[0] != "isl":
            await self._telegram.answer_callback_query(
                callback_query_id=callback.id, text="Aksi tidak dikenali."
            )
            return
        scope = await self._service.ensure_scope(
            chat_id=context.chat_id, chat_type=context.chat_type
        )
        group, action, raw_value = parts[1], parts[2], parts[3]
        try:
            await self._telegram.answer_callback_query(callback_query_id=callback.id)
            if group == "setup":
                if callback.message is not None:
                    previous = await self._service.replace_setup_message(
                        scope.id, callback.message.message_id
                    )
                    await self._cleanup(scope.chat_id, previous)
                await self._setup_callback(scope, action, raw_value)
            elif group == "quran":
                await self._quran_callback(scope, action)
            elif group == "mode":
                session = await self._service.choose_mode(scope.id, int(raw_value), action)
                if callback.message is not None:
                    await self._cleanup(scope.chat_id, [callback.message.message_id])
                await self._send_next_batch(scope, session.id)
            elif group == "session":
                session_id = int(raw_value)
                if action == "cancel":
                    await self._cleanup(
                        scope.chat_id,
                        await self._service.cancel_session(scope.id, session_id),
                    )
                    await self._send(scope.chat_id, "Sesi baca dibatalkan.")
                elif action == "resume":
                    session = await self._service.active_session(scope.id, session_id)
                    if session.mode is None:
                        sent = await self._telegram.send_message(
                            chat_id=scope.chat_id,
                            text="Pilih mode sesi baca:",
                            reply_markup={"inline_keyboard": [[
                                {"text": "PC", "callback_data": f"isl:mode:pc:{session.id}"},
                                {"text": "Mobile", "callback_data": f"isl:mode:mobile:{session.id}"},
                            ]]},
                        )
                        await self._service.attach_prompt(session.id, sent.message_id)
                    else:
                        await self._send_next_batch(scope, session_id)
            elif group == "read":
                await self._mark_read(scope, int(raw_value), int(action), callback)
            elif group == "batch" and action == "read":
                await self._mark_batch(scope, int(raw_value))
        except (IslamicInputError, ValueError) as error:
            await self._send(scope.chat_id, escape(str(error)))

    async def _setup_callback(self, scope: ScopeValue, action: str, raw: str) -> None:
        if action == "location":
            await self._service.set_setup_state(scope.id, "setup_await_location", {})
            if scope.chat_type == "private":
                await self._replace_setup_message(
                    scope,
                    chat_id=scope.chat_id,
                    text="Tekan tombol berikut untuk membagikan lokasi:",
                    reply_markup={
                        "keyboard": [[{"text": "📍 Kirim lokasi", "request_location": True}]],
                        "resize_keyboard": True,
                        "one_time_keyboard": True,
                    },
                )
            else:
                await self._replace_setup_message(
                    scope,
                    chat_id=scope.chat_id,
                    text="Kirim attachment Location sebagai balasan pesan ini. Tombol request_location hanya tersedia di private chat.",
                )
        elif action == "city":
            await self._service.set_setup_state(scope.id, "setup_await_city", {})
            await self._replace_setup_message(
                scope,
                chat_id=scope.chat_id,
                text="Ketik kota dan negara, contoh: Jakarta, Indonesia",
                reply_markup={"force_reply": True, "selective": True},
            )
        elif action == "coords":
            await self._service.set_setup_state(scope.id, "setup_await_coords", {})
            await self._replace_setup_message(
                scope,
                chat_id=scope.chat_id,
                text="Ketik latitude, longitude, dan opsional timezone.",
                reply_markup={"force_reply": True, "selective": True},
            )
        elif action == "auto":
            await self._choose_method(scope, None)
        elif action == "method":
            await self._choose_method(scope, int(raw))
        elif action == "methods":
            await self._show_methods_page(scope, int(raw))
        elif action == "tzok":
            scope = await self._service.merge_setup_data(
                scope.id, state="setup_confirm", values={}
            )
            await self._show_setup_confirmation(scope)
        elif action == "tzchange":
            await self._service.merge_setup_data(
                scope.id, state="setup_await_timezone", values={}
            )
            await self._replace_setup_message(
                scope,
                chat_id=scope.chat_id,
                text="Ketik timezone IANA, contoh: Asia/Jakarta",
                reply_markup={"force_reply": True, "selective": True},
            )
        elif action == "save":
            configured, cleanup = await self._service.apply_setup(scope.id)
            await self._telegram.send_message(
                chat_id=configured.chat_id,
                text=f"Setup tersimpan. Timezone: <code>{escape(configured.timezone)}</code>.",
                parse_mode="HTML",
                reply_markup={"remove_keyboard": True},
            )
            await self._cleanup(configured.chat_id, cleanup)
        elif action == "cancel":
            cleanup = await self._service.cancel_setup(scope.id)
            await self._telegram.send_message(
                chat_id=scope.chat_id,
                text="Setup dibatalkan.",
                reply_markup={"remove_keyboard": True},
            )
            await self._cleanup(scope.chat_id, cleanup)

    async def _quran_callback(self, scope: ScopeValue, action: str) -> None:
        if action == "start":
            scope = await self._service.set_setup_state(
                scope.id, "quran_confirm", {"start": True}
            )
            await self._show_progress_confirmation(scope, None)
        elif action == "page":
            await self._service.set_setup_state(scope.id, "quran_await_page", {})
            await self._telegram.send_message(
                chat_id=scope.chat_id,
                text="Ketik halaman terakhir yang sudah selesai (1-604).",
                reply_markup={"force_reply": True, "selective": True},
            )
        elif action == "ayah":
            await self._service.set_setup_state(scope.id, "quran_await_ayah", {})
            await self._telegram.send_message(
                chat_id=scope.chat_id,
                text="Ketik ayat terakhir, contoh: 2:255",
                reply_markup={"force_reply": True, "selective": True},
            )
        elif action == "save":
            current = await self._service.scope(chat_id=scope.chat_id)
            if current is None or current.setup_state != "quran_confirm":
                raise IslamicInputError("Konfirmasi progress sudah kedaluwarsa.")
            raw = current.setup_data.get("ayah")
            ayah = None
            if isinstance(raw, dict):
                ayah = AyahValue(
                    number=int(raw["number"]),
                    surah_number=int(raw["surah_number"]),
                    surah_name=str(raw["surah_name"]),
                    number_in_surah=int(raw["number_in_surah"]),
                    page=int(raw["page"]),
                )
            cleanup = await self._service.set_progress(scope.id, ayah)
            await self._service.set_setup_state(scope.id, None, {})
            await self._cleanup(scope.chat_id, cleanup)
            await self._send(scope.chat_id, "Progress Quran tersimpan.")
        elif action == "cancel":
            await self._service.set_setup_state(scope.id, None, {})
            await self._send(scope.chat_id, "Perubahan progress dibatalkan.")

    async def _mark_read(
        self,
        scope: ScopeValue,
        session_id: int,
        ayah_number: int,
        callback: TelegramCallbackQuery,
    ) -> None:
        update = await self._service.mark_read(
            scope.id, session_id, ayah_number=ayah_number
        )
        if callback.message is not None and not update.batch_complete:
            await self._telegram.edit_message_reply_markup(
                chat_id=scope.chat_id,
                message_id=callback.message.message_id,
                reply_markup={"inline_keyboard": [[{
                    "text": "✅ Read",
                    "callback_data": f"isl:read:{ayah_number}:{session_id}",
                }]]},
            )
        await self._advance_after_read(scope, update)

    async def _mark_batch(self, scope: ScopeValue, session_id: int) -> None:
        update = await self._service.mark_read(
            scope.id, session_id, whole_batch=True
        )
        await self._advance_after_read(scope, update)

    async def _advance_after_read(self, scope: ScopeValue, update: Any) -> None:
        if not update.batch_complete:
            return
        await self._cleanup(scope.chat_id, update.delete_message_ids)
        if update.session_complete:
            progress = await self._service.progress(scope.id)
            await self._send(
                scope.chat_id,
                f"Sesi selesai. Terakhir: <b>{escape(str(progress.last_surah_name))} "
                f"{progress.last_surah_number}:{progress.last_ayah_in_surah}</b>, halaman {progress.last_page}.",
            )
        else:
            await self._send_next_batch(scope, update.session.id)

    async def _cleanup(self, chat_id: int, message_ids: list[int]) -> None:
        for message_id in dict.fromkeys(message_ids):
            try:
                await self._telegram.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass

    async def _replace_setup_message(
        self,
        scope: ScopeValue,
        *,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        sent = await self._telegram.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        previous = await self._service.replace_setup_message(scope.id, sent.message_id)
        await self._cleanup(chat_id, previous)

    async def _send(self, chat_id: int, text: str) -> None:
        await self._telegram.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

    @staticmethod
    def _help_text() -> str:
        return (
            "<b>Adzan & Quran</b>\n"
            "/setup — lokasi, timezone, dan metode adzan\n"
            "/quran — atur posisi terakhir\n"
            "/read 1p — baca berdasarkan halaman\n"
            "/read 5a — baca berdasarkan jumlah ayat\n"
            "/stats — statistik chat ini"
        )
