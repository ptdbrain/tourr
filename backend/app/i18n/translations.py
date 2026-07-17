"""
Tour-resQ Internationalization System
=====================================
Complete translation system for KO/ZH/EN/RU.

Design decisions:
- Translations are flat dicts keyed by dot-notation (e.g., "price.fair")
- Every user-facing string MUST go through t(key, lang) — no hardcoded strings
- Tourist-specific phrasing: simple, direct, calming in emergencies
- Cultural awareness: formal register for KO/ZH, direct for EN, formal for RU
"""

from typing import Optional


# ─────────────────────────────────────────────────────────
# TRANSLATION DICTIONARY
# ─────────────────────────────────────────────────────────
# Keys use dot notation: category.subcategory.item
# Every key MUST have all 4 languages

TRANSLATIONS: dict[str, dict[str, str]] = {

    # ── App General ──────────────────────────────────────
    "app.name": {
        "en": "Tour-resQ",
        "ko": "Tour-resQ",
        "zh": "Tour-resQ",
        "ru": "Tour-resQ",
    },
    "app.tagline": {
        "en": "Your safety companion in Vietnam",
        "ko": "베트남에서의 안전 도우미",
        "zh": "您在越南的安全伙伴",
        "ru": "Ваш помощник безопасности во Вьетнаме",
    },
    "app.welcome": {
        "en": "Welcome to Vietnam! We're here to help you stay safe.",
        "ko": "베트남에 오신 것을 환영합니다! 안전한 여행을 도와드리겠습니다.",
        "zh": "欢迎来到越南！我们将帮助您安全出行。",
        "ru": "Добро пожаловать во Вьетнам! Мы поможем вам быть в безопасности.",
    },

    # ── Language Selection (shown as native text) ────────
    "lang.select": {
        "en": "Choose your language",
        "ko": "언어를 선택하세요",
        "zh": "选择您的语言",
        "ru": "Выберите язык",
    },
    "lang.en": {
        "en": "English",
        "ko": "English",
        "zh": "English",
        "ru": "English",
    },
    "lang.ko": {
        "en": "한국어",
        "ko": "한국어",
        "zh": "한국어",
        "ru": "한국어",
    },
    "lang.zh": {
        "en": "中文",
        "ko": "中文",
        "zh": "中文",
        "ru": "中文",
    },
    "lang.ru": {
        "en": "Русский",
        "ko": "Русский",
        "zh": "Русский",
        "ru": "Русский",
    },

    # ── Navigation / Main Actions ────────────────────────
    "nav.price_check": {
        "en": "Check Price",
        "ko": "가격 확인",
        "zh": "价格检查",
        "ru": "Проверить цену",
    },
    "nav.scam_help": {
        "en": "Scam Help",
        "ko": "사기 도움",
        "zh": "防骗帮助",
        "ru": "Помощь с мошенничеством",
    },
    "nav.translate": {
        "en": "Translate",
        "ko": "번역",
        "zh": "翻译",
        "ru": "Перевод",
    },
    "nav.sos": {
        "en": "SOS Emergency",
        "ko": "SOS 긴급",
        "zh": "SOS 紧急求助",
        "ru": "SOS Экстренная помощь",
    },
    "nav.phrasebook": {
        "en": "Quick Phrases",
        "ko": "빠른 문구",
        "zh": "常用短语",
        "ru": "Быстрые фразы",
    },
    "nav.phrasebook_desc": {
        "en": "Common phrases to show vendors",
        "ko": "판매자에게 보여줄 일반 문구",
        "zh": "向商家展示的常用短语",
        "ru": "Фразы для показа продавцам",
    },
    "sos.tap_to_send": {
        "en": "Tap to send your location",
        "ko": "탭하여 위치를 전송하세요",
        "zh": "点击发送您的位置",
        "ru": "Нажмите, чтобы отправить ваше местоположение",
    },

    # ── Price Check Module ───────────────────────────────
    "price.region": {
        "en": "📍 Region:",
        "ko": "📍 지역:",
        "zh": "📍 地区：",
        "ru": "📍 Регион:",
    },
    "price.manual_entry": {
        "en": "Or enter manually:",
        "ko": "또는 직접 입력:",
        "zh": "或手动输入：",
        "ru": "Или введите вручную:",
    },
    "price.instruction": {
        "en": "Take a photo of the receipt, menu, or price board",
        "ko": "영수증, 메뉴 또는 가격표 사진을 찍어주세요",
        "zh": "拍一张收据、菜单或价格牌的照片",
        "ru": "Сфотографируйте чек, меню или ценник",
    },
    "price.analyzing": {
        "en": "Analyzing prices...",
        "ko": "가격 분석 중...",
        "zh": "正在分析价格...",
        "ru": "Анализ цен...",
    },
    "price.fair": {
        "en": "✅ Fair Price — This price is within the normal range for this area.",
        "ko": "✅ 적정 가격 — 이 지역의 정상 가격 범위 내입니다.",
        "zh": "✅ 合理价格 — 此价格在该地区的正常范围内。",
        "ru": "✅ Справедливая цена — Эта цена в пределах нормы для данного района.",
    },
    "price.slightly_high": {
        "en": "⚠️ Slightly Above Average — This price is a bit higher than usual, but may be normal for this type of establishment.",
        "ko": "⚠️ 약간 높음 — 평균보다 약간 높지만, 이런 유형의 가게에서는 정상일 수 있습니다.",
        "zh": "⚠️ 略高于平均 — 此价格略高于平时，但对于这类场所可能是正常的。",
        "ru": "⚠️ Немного выше среднего — Цена чуть выше обычной, но может быть нормальной для данного заведения.",
    },
    "price.overpriced": {
        "en": "🔴 Significantly Overpriced — This price is much higher than the regional average. You may want to verify or negotiate.",
        "ko": "🔴 과도한 가격 — 이 가격은 지역 평균보다 훨씬 높습니다. 확인하거나 협상하는 것이 좋겠습니다.",
        "zh": "🔴 明显偏高 — 此价格远高于该地区平均水平。建议您核实或协商。",
        "ru": "🔴 Значительно завышена — Эта цена намного выше средней по району. Рекомендуем проверить или поторговаться.",
    },
    "price.insufficient_data": {
        "en": "ℹ️ Insufficient Data — We don't have enough data to assess this price confidently. The price may or may not be fair.",
        "ko": "ℹ️ 데이터 부족 — 이 가격을 확실하게 평가할 충분한 데이터가 없습니다. 가격이 적정할 수도, 아닐 수도 있습니다.",
        "zh": "ℹ️ 数据不足 — 我们没有足够的数据来确信地评估此价格。价格可能合理，也可能不合理。",
        "ru": "ℹ️ Недостаточно данных — У нас недостаточно данных для уверенной оценки этой цены. Цена может быть как справедливой, так и нет.",
    },
    "price.based_on": {
        "en": "Based on {count} similar transactions in this area",
        "ko": "이 지역의 {count}건의 유사 거래를 기준으로 합니다",
        "zh": "基于该地区 {count} 笔类似交易",
        "ru": "На основе {count} аналогичных сделок в этом районе",
    },
    "price.range": {
        "en": "Typical price range: {min} – {max} VND",
        "ko": "일반 가격 범위: {min} – {max} VND",
        "zh": "一般价格范围：{min} – {max} 越南盾",
        "ru": "Обычный диапазон цен: {min} – {max} VND",
    },
    "price.your_price": {
        "en": "Your price: {price} VND",
        "ko": "귀하의 가격: {price} VND",
        "zh": "您的价格：{price} 越南盾",
        "ru": "Ваша цена: {price} VND",
    },
    "price.percent_above": {
        "en": "{percent}% above the average",
        "ko": "평균보다 {percent}% 높음",
        "zh": "高于平均 {percent}%",
        "ru": "На {percent}% выше среднего",
    },

    # ── Scam Detection Module ────────────────────────────
    "scam.instruction": {
        "en": "Describe what happened — speak or type",
        "ko": "무슨 일이 있었는지 말씀하거나 입력해 주세요",
        "zh": "描述发生了什么 — 说话或输入",
        "ru": "Опишите, что произошло — голосом или текстом",
    },
    "scam.analyzing": {
        "en": "Analyzing the situation...",
        "ko": "상황 분석 중...",
        "zh": "正在分析情况...",
        "ru": "Анализ ситуации...",
    },
    "scam.detected": {
        "en": "⚠️ This matches a known scam pattern",
        "ko": "⚠️ 알려진 사기 패턴과 일치합니다",
        "zh": "⚠️ 这与已知的诈骗模式匹配",
        "ru": "⚠️ Это совпадает с известной схемой мошенничества",
    },
    "scam.advice_prefix": {
        "en": "Here's what you can do:",
        "ko": "다음과 같이 할 수 있습니다:",
        "zh": "您可以这样做：",
        "ru": "Вот что вы можете сделать:",
    },
    "scam.not_detected": {
        "en": "We didn't detect a known scam pattern, but stay cautious. If you feel unsafe, use the SOS button.",
        "ko": "알려진 사기 패턴이 감지되지 않았지만, 주의하세요. 불안하면 SOS 버튼을 사용하세요.",
        "zh": "未检测到已知诈骗模式，但请保持警惕。如果您感到不安全，请使用SOS按钮。",
        "ru": "Мы не обнаружили известную схему мошенничества, но будьте осторожны. Если чувствуете угрозу, используйте кнопку SOS.",
    },

    # ── Common Scam Patterns ─────────────────────────────
    "scam.pattern.taxi_meter": {
        "en": "🚕 Taxi Meter Scam — The taxi meter may be tampered with or the driver is taking a longer route.",
        "ko": "🚕 택시 미터 사기 — 택시 미터가 조작되었거나 운전기사가 먼 길을 돌아가고 있을 수 있습니다.",
        "zh": "🚕 出租车计价器骗局 — 出租车计价器可能被篡改，或司机在绕远路。",
        "ru": "🚕 Обман с таксометром — Счётчик такси может быть подделан или водитель едет длинным маршрутом.",
    },
    "scam.pattern.overcharge": {
        "en": "💰 Overcharging — You're being charged significantly more than the fair price.",
        "ko": "💰 바가지 요금 — 적정 가격보다 훨씬 높은 금액이 청구되고 있습니다.",
        "zh": "💰 过度收费 — 您被收取的费用远高于合理价格。",
        "ru": "💰 Завышение цены — С вас берут значительно больше, чем справедливая цена.",
    },
    "scam.pattern.ghost_tour": {
        "en": "👻 Ghost Tour Scam — A tour that was promised but doesn't actually exist or doesn't match what was advertised.",
        "ko": "👻 유령 투어 사기 — 약속했지만 실제로 존재하지 않거나 광고와 다른 투어입니다.",
        "zh": "👻 虚假旅游团 — 承诺的旅游团实际上不存在或与广告不符。",
        "ru": "👻 Мошенничество с турами — Тур, который обещали, но который не существует или не соответствует рекламе.",
    },
    "scam.pattern.money_exchange": {
        "en": "💱 Money Exchange Scam — You may be receiving a very unfair exchange rate or counterfeit bills.",
        "ko": "💱 환전 사기 — 매우 불공정한 환율을 적용받거나 위조지폐를 받을 수 있습니다.",
        "zh": "💱 换汇骗局 — 您可能收到非常不公平的汇率或假钞。",
        "ru": "💱 Обман при обмене валюты — Вам могут дать очень невыгодный курс или фальшивые купюры.",
    },
    "scam.pattern.shoe_shine": {
        "en": "👟 Forced Service Scam — Someone is performing a service you didn't ask for and demanding payment.",
        "ko": "👟 강제 서비스 사기 — 요청하지 않은 서비스를 제공하고 돈을 요구합니다.",
        "zh": "👟 强制服务骗局 — 有人在提供您未要求的服务并要求付款。",
        "ru": "👟 Навязывание услуг — Кто-то оказывает услугу, которую вы не просили, и требует оплату.",
    },

    # ── Scam Advice ──────────────────────────────────────
    "advice.taxi_meter": {
        "en": "• Ask to see the meter and compare with Grab/Be app estimate\n• Take a photo of the meter and the license plate\n• Fair taxi rates: ~12,000-15,000 VND per km\n• Call the tourist hotline: 1900-6068",
        "ko": "• 미터를 확인하고 Grab/Be 앱 추정치와 비교하세요\n• 미터와 번호판 사진을 찍어두세요\n• 적정 택시 요금: km당 약 12,000-15,000 VND\n• 관광 핫라인: 1900-6068",
        "zh": "• 要求查看计价器并与Grab/Be应用估价对比\n• 拍下计价器和车牌号的照片\n• 合理出租车费：约12,000-15,000越南盾/公里\n• 拨打旅游热线：1900-6068",
        "ru": "• Попросите показать счётчик и сравните с оценкой в приложении Grab/Be\n• Сфотографируйте счётчик и номерной знак\n• Справедливый тариф: ~12 000-15 000 VND за км\n• Позвоните на горячую линию: 1900-6068",
    },
    "advice.overcharge": {
        "en": "• Stay calm and polite\n• Show the price check result on your phone\n• Ask for an itemized receipt\n• Politely negotiate or say you'll check online\n• If threatened, leave and call 113 (police)",
        "ko": "• 침착하고 예의 바르게 대하세요\n• 휴대폰의 가격 확인 결과를 보여주세요\n• 항목별 영수증을 요청하세요\n• 정중하게 협상하거나 온라인에서 확인하겠다고 말하세요\n• 위협받으면 자리를 떠나고 113(경찰)에 전화하세요",
        "zh": "• 保持冷静和礼貌\n• 展示手机上的价格检查结果\n• 要求出具明细收据\n• 礼貌地协商或说您要在网上查一下\n• 如果受到威胁，离开并拨打113（报警）",
        "ru": "• Сохраняйте спокойствие и вежливость\n• Покажите результат проверки цены на телефоне\n• Попросите детализированный чек\n• Вежливо поторгуйтесь или скажите, что проверите в интернете\n• Если угрожают, уходите и звоните 113 (полиция)",
    },
    "advice.ghost_tour": {
        "en": "• Never pay full price upfront for a tour\n• Check reviews on Google Maps/TripAdvisor\n• Ask for a printed itinerary before paying\n• Only book through licensed tour companies\n• Report to tourism hotline: 1900-6068",
        "ko": "• 투어 비용을 미리 전액 지불하지 마세요\n• Google Maps/TripAdvisor에서 리뷰를 확인하세요\n• 결제 전에 인쇄된 일정표를 요청하세요\n• 허가된 여행사를 통해서만 예약하세요\n• 관광 핫라인에 신고: 1900-6068",
        "zh": "• 不要预付旅游全款\n• 在Google Maps/TripAdvisor上查看评价\n• 付款前要求打印行程单\n• 只通过持牌旅行社预订\n• 向旅游热线举报：1900-6068",
        "ru": "• Никогда не платите полную сумму за тур заранее\n• Проверьте отзывы на Google Maps/TripAdvisor\n• Попросите распечатанный маршрут перед оплатой\n• Бронируйте только через лицензированные компании\n• Сообщите на горячую линию: 1900-6068",
    },
    "advice.money_exchange": {
        "en": "• Only exchange at banks or official exchange counters\n• Check the current rate on Google before exchanging\n• Count money carefully before leaving the counter\n• Beware of 'commission fees' not mentioned upfront\n• Report suspicious exchange shops to police",
        "ko": "• 은행이나 공식 환전소에서만 환전하세요\n• 환전 전 Google에서 현재 환율을 확인하세요\n• 카운터를 떠나기 전에 돈을 꼼꼼히 세어보세요\n• 사전에 언급되지 않은 '수수료'에 주의하세요\n• 의심스러운 환전소는 경찰에 신고하세요",
        "zh": "• 只在银行或官方换汇柜台换钱\n• 换汇前在Google上查看当前汇率\n• 离开柜台前仔细点钱\n• 小心事先未提及的「手续费」\n• 向警方举报可疑的换汇店",
        "ru": "• Меняйте валюту только в банках или официальных обменных пунктах\n• Проверьте текущий курс в Google перед обменом\n• Тщательно пересчитайте деньги перед уходом\n• Остерегайтесь «комиссий», не упомянутых заранее\n• Сообщите о подозрительных обменных пунктах в полицию",
    },
    "advice.shoe_shine": {
        "en": "• Firmly say NO and walk away\n• Do not engage or let them start\n• If they persist, say 'I will call the police'\n• Do not feel obligated to pay for unsolicited services\n• Move to a crowded area",
        "ko": "• 단호하게 거절하고 자리를 피하세요\n• 대화하거나 서비스를 시작하게 두지 마세요\n• 계속 따라오면 '경찰을 부르겠다'고 말하세요\n• 요청하지 않은 서비스에 대해 돈을 낼 의무는 없습니다\n• 사람이 많은 곳으로 이동하세요",
        "zh": "• 坚定地说「不」然后走开\n• 不要搭理或让他们开始\n• 如果他们坚持，说「我要报警」\n• 不要觉得有义务为未请求的服务付款\n• 移动到人多的地方",
        "ru": "• Твёрдо скажите НЕТ и уходите\n• Не вступайте в контакт и не позволяйте начинать\n• Если настаивают, скажите «Я вызову полицию»\n• Вы не обязаны платить за непрошеные услуги\n• Перейдите в людное место",
    },

    # ── SOS / Emergency ──────────────────────────────────
    "sos.title": {
        "en": "🚨 EMERGENCY SOS",
        "ko": "🚨 긴급 SOS",
        "zh": "🚨 紧急求助 SOS",
        "ru": "🚨 ЭКСТРЕННАЯ ПОМОЩЬ SOS",
    },
    "sos.activating": {
        "en": "Sending your location and details to emergency services...",
        "ko": "위치와 세부 정보를 긴급 서비스에 전송하는 중...",
        "zh": "正在将您的位置和详情发送给紧急服务...",
        "ru": "Отправка вашего местоположения и данных в экстренные службы...",
    },
    "sos.sent": {
        "en": "✅ Your SOS has been sent! Help is on the way.",
        "ko": "✅ SOS가 전송되었습니다! 도움이 오고 있습니다.",
        "zh": "✅ 您的SOS已发送！救援正在赶来。",
        "ru": "✅ Ваш SOS отправлен! Помощь уже в пути.",
    },
    "sos.call_police": {
        "en": "Call Police: 113",
        "ko": "경찰 전화: 113",
        "zh": "报警电话：113",
        "ru": "Вызов полиции: 113",
    },
    "sos.call_tourist_hotline": {
        "en": "Tourism Hotline: 1900-6068",
        "ko": "관광 핫라인: 1900-6068",
        "zh": "旅游热线：1900-6068",
        "ru": "Горячая линия туризма: 1900-6068",
    },
    "sos.call_tourist_police": {
        "en": "Tourist Police (Hanoi): 024-3942-8828",
        "ko": "관광 경찰 (하노이): 024-3942-8828",
        "zh": "旅游警察（河内）：024-3942-8828",
        "ru": "Туристическая полиция (Ханой): 024-3942-8828",
    },
    "sos.stay_calm": {
        "en": "Stay calm. Do not leave the area if possible. Stay on the phone.",
        "ko": "침착하세요. 가능하면 현장을 떠나지 마세요. 통화를 유지하세요.",
        "zh": "请保持冷静。如果可能，不要离开现场。保持通话。",
        "ru": "Сохраняйте спокойствие. По возможности не покидайте место. Оставайтесь на связи.",
    },
    "sos.share_location": {
        "en": "Share your live location with a friend",
        "ko": "친구에게 실시간 위치를 공유하세요",
        "zh": "与朋友分享您的实时位置",
        "ru": "Поделитесь своим местоположением с другом",
    },

    # ── Translation Module ───────────────────────────────
    "translate.instruction": {
        "en": "Speak or type what you want to say in Vietnamese",
        "ko": "베트남어로 말하고 싶은 것을 말하거나 입력하세요",
        "zh": "说或输入您想用越南语表达的内容",
        "ru": "Скажите или введите то, что хотите сказать по-вьетнамски",
    },
    "translate.to_vietnamese": {
        "en": "→ Vietnamese",
        "ko": "→ 베트남어",
        "zh": "→ 越南语",
        "ru": "→ Вьетнамский",
    },
    "translate.from_vietnamese": {
        "en": "→ Your language",
        "ko": "→ 한국어",
        "zh": "→ 中文",
        "ru": "→ Русский",
    },
    "translate.speak_now": {
        "en": "🎤 Speak now...",
        "ko": "🎤 지금 말씀하세요...",
        "zh": "🎤 请说话...",
        "ru": "🎤 Говорите...",
    },
    "translate.show_to_vendor": {
        "en": "Show this to the vendor ↓",
        "ko": "이것을 판매자에게 보여주세요 ↓",
        "zh": "把这个给商家看 ↓",
        "ru": "Покажите это продавцу ↓",
    },

    # ── Contextual Onboarding ────────────────────────────
    "onboard.airport_welcome": {
        "en": "🛬 You just arrived! Here are the top 3 things to watch out for:",
        "ko": "🛬 방금 도착하셨군요! 주의해야 할 3가지:",
        "zh": "🛬 您刚到达！以下是需要注意的3件事：",
        "ru": "🛬 Вы только прибыли! Вот 3 главных совета:",
    },
    "onboard.tip_taxi": {
        "en": "🚕 Use Grab or Be apps for taxis. Avoid unmarked vehicles.",
        "ko": "🚕 택시는 Grab 또는 Be 앱을 사용하세요. 표시 없는 차량을 피하세요.",
        "zh": "🚕 打车请使用Grab或Be应用。避免乘坐无标识车辆。",
        "ru": "🚕 Используйте приложения Grab или Be для такси. Избегайте машин без опознавательных знаков.",
    },
    "onboard.tip_bargain": {
        "en": "💬 Bargaining is normal at markets. Start at 50% of the asking price.",
        "ko": "💬 시장에서 흥정은 일반적입니다. 제시가의 50%부터 시작하세요.",
        "zh": "💬 在市场讲价是正常的。从要价的50%开始还价。",
        "ru": "💬 Торговаться на рынках — это нормально. Начинайте с 50% от запрашиваемой цены.",
    },
    "onboard.tip_exchange": {
        "en": "💱 Exchange money only at banks or official counters. Check rates on Google first.",
        "ko": "💱 은행이나 공식 환전소에서만 환전하세요. Google에서 먼저 환율을 확인하세요.",
        "zh": "💱 只在银行或官方柜台换钱。先在Google上查看汇率。",
        "ru": "💱 Меняйте деньги только в банках или официальных обменниках. Сначала проверьте курс в Google.",
    },

    # ── Errors & Status ──────────────────────────────────
    "error.generic": {
        "en": "Something went wrong. Please try again.",
        "ko": "오류가 발생했습니다. 다시 시도해 주세요.",
        "zh": "出了点问题。请重试。",
        "ru": "Что-то пошло не так. Пожалуйста, попробуйте снова.",
    },
    "error.no_camera": {
        "en": "Camera not available. Please check permissions.",
        "ko": "카메라를 사용할 수 없습니다. 권한을 확인해 주세요.",
        "zh": "相机不可用。请检查权限。",
        "ru": "Камера недоступна. Проверьте разрешения.",
    },
    "error.no_location": {
        "en": "Location not available. Please enable GPS for SOS.",
        "ko": "위치를 사용할 수 없습니다. SOS를 위해 GPS를 활성화해 주세요.",
        "zh": "位置不可用。请为SOS启用GPS。",
        "ru": "Местоположение недоступно. Включите GPS для SOS.",
    },
    "error.offline": {
        "en": "You're offline. Basic features still work.",
        "ko": "오프라인 상태입니다. 기본 기능은 계속 사용 가능합니다.",
        "zh": "您已离线。基本功能仍然可用。",
        "ru": "Вы не в сети. Основные функции всё ещё работают.",
    },
    "status.loading": {
        "en": "Loading...",
        "ko": "로딩 중...",
        "zh": "加载中...",
        "ru": "Загрузка...",
    },
    "status.ready": {
        "en": "Ready",
        "ko": "준비 완료",
        "zh": "就绪",
        "ru": "Готово",
    },

    # ── Useful Phrases for Confrontation ─────────────────
    "phrase.show_meter": {
        "en": "Please show me the meter",
        "ko": "미터를 보여주세요",
        "zh": "请让我看一下计价器",
        "ru": "Пожалуйста, покажите мне счётчик",
        "vi": "Làm ơn cho tôi xem đồng hồ",
    },
    "phrase.too_expensive": {
        "en": "This is too expensive",
        "ko": "이것은 너무 비쌉니다",
        "zh": "这太贵了",
        "ru": "Это слишком дорого",
        "vi": "Cái này đắt quá",
    },
    "phrase.call_police": {
        "en": "I will call the police",
        "ko": "경찰을 부르겠습니다",
        "zh": "我要报警",
        "ru": "Я вызову полицию",
        "vi": "Tôi sẽ gọi công an",
    },
    "phrase.give_receipt": {
        "en": "Please give me a receipt",
        "ko": "영수증을 주세요",
        "zh": "请给我一张收据",
        "ru": "Пожалуйста, дайте мне чек",
        "vi": "Làm ơn cho tôi hóa đơn",
    },
    "phrase.original_price": {
        "en": "What is the original price?",
        "ko": "원래 가격이 얼마인가요?",
        "zh": "原价是多少？",
        "ru": "Какая первоначальная цена?",
        "vi": "Giá gốc là bao nhiêu?",
    },
    "phrase.no_thank_you": {
        "en": "No, thank you",
        "ko": "아니요, 괜찮습니다",
        "zh": "不用了，谢谢",
        "ru": "Нет, спасибо",
        "vi": "Không, cảm ơn",
    },
    "phrase.i_dont_want": {
        "en": "I don't want this service",
        "ko": "이 서비스를 원하지 않습니다",
        "zh": "我不需要这个服务",
        "ru": "Мне не нужна эта услуга",
        "vi": "Tôi không muốn dịch vụ này",
    },
}


# ─────────────────────────────────────────────────────────
# TRANSLATION FUNCTION
# ─────────────────────────────────────────────────────────

def t(key: str, lang: str = "en", **kwargs) -> str:
    """
    Get a translated string.

    Args:
        key: Dot-notation key (e.g., "price.fair")
        lang: Language code ("en", "ko", "zh", "ru")
        **kwargs: Format parameters (e.g., count=147, min="35,000")

    Returns:
        Translated string with parameters substituted.
        Falls back to English if key/language not found.
    """
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return f"[{key}]"  # Missing key — visible during development

    text = entry.get(lang) or entry.get("en", f"[{key}]")

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass  # Return unformatted text if params don't match

    return text


def get_all_translations(lang: str = "en") -> dict[str, str]:
    """
    Get all translations for a language as a flat dict.
    Useful for sending to frontend in one batch.
    """
    result = {}
    for key, entry in TRANSLATIONS.items():
        result[key] = entry.get(lang) or entry.get("en", "")
    return result


def get_supported_languages() -> list[dict]:
    """
    Get list of supported languages with display info.
    Returns flag emoji + native name for UI rendering.
    """
    return [
        {"code": "en", "name": "English", "flag": "🇬🇧", "native": "English"},
        {"code": "ko", "name": "Korean", "flag": "🇰🇷", "native": "한국어"},
        {"code": "zh", "name": "Chinese", "flag": "🇨🇳", "native": "中文"},
        {"code": "ru", "name": "Russian", "flag": "🇷🇺", "native": "Русский"},
    ]
