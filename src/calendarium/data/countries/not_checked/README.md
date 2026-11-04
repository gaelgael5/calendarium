# Unverified configurations

These country files are imported from the original project and are **not
verified**: their holiday lists have not been reviewed against official
sources, and most of them cannot be completed with the current engine.
They load only with `Calendarium.bundled(include_not_checked=True)` or the
CLI flag `--all`.

Everything that could be verified has been promoted to `data/countries/`
(see the per-country git history and `tests/golden/`). What remains here is
blocked, country by country:

| Country | Blocking reason |
|---|---|
| Brunei | Chinese New Year and Islamic days set by official sighting; lunisolar calendar not implemented |
| China | Chinese lunisolar calendar (Spring Festival, Qingming, Dragon Boat, Mid-Autumn) not implemented; yearly State Council bridge/make-up days are decree-based |
| Hong_Kong_S_A_R | Chinese lunisolar calendar (Lunar New Year, Ching Ming, Buddha's Birthday, Tuen Ng, Mid-Autumn, Chung Yeung) not implemented |
| Korea | Korean lunisolar calendar (Seollal, Buddha's Birthday, Chuseok) not implemented |
| Macao_S_A_R | Chinese lunisolar calendar, as Hong Kong |
| Malaysia | Chinese New Year, Wesak, Deepavali and Thaipusam require lunisolar/Hindu dates; state-level variation |
| Singapore | Chinese New Year, Vesak and Deepavali require lunisolar/Hindu dates |
| Syria | Holiday list in flux after the December 2024 change of government; needs a stable official source |
| Thailand | Buddhist lunar days (Makha/Visakha/Asarnha Bucha, Khao Phansa) require the Thai lunar calendar |
| Trinidad_and_Tobago | Divali is gazetted yearly from Hindu calendar dates, not implemented |
| Vietnam | Tet and Hung Kings' Day require the Vietnamese lunisolar calendar |

Unblocking most of this list means implementing an astronomical Chinese
lunisolar calendar (which would also cover Korea, Vietnam and the
Mid-Autumn family) and gazetted-table functions like `[MATARIKI]` for
Divali and the Thai Buddhist days.
