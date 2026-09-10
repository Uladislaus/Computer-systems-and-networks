"""Каталог типов документов и полей формы."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    multiline: bool = False
    default: str = ""


@dataclass(frozen=True)
class DocType:
    id: str
    title: str
    category: str
    description: str
    fields: tuple[Field, ...] = field(default_factory=tuple)
    filename: str = "document.docx"


COMMON_ORG = (
    Field("org", "Организация", default='ГУ «Белгидромет»'),
    Field("podrazdelenie", "Подразделение", default="Служба программного обеспечения"),
)

CATALOG: tuple[DocType, ...] = (
    DocType(
        id="doklad_o_prodelannoy_rabote",
        title="Доклад о проделанной работе",
        category="Отчёты",
        description="Доклад/отчёт по завершении темы или программы (например, кубический сплайн): цель, ход работ, результаты, выводы.",
        filename="Doklad_o_prodelannoy_rabote.docx",
        fields=COMMON_ORG
        + (
            Field("tema", "Тема / программа / проект", default="Кубический сплайн"),
            Field("fio", "ФИО докладчика"),
            Field("dolzhnost", "Должность"),
            Field("period", "Срок выполнения"),
            Field("data", "Дата доклада", default="«____» ______________ 202__ г."),
            Field("cel", "Цель работы", multiline=True),
            Field("iskhodnye", "Исходные данные / постановка", multiline=True),
            Field("vypolneno", "Что сделано (этапы)", multiline=True),
            Field("rezultaty", "Результаты", multiline=True),
            Field("produkty", "Документы / код / материалы на выходе", multiline=True),
            Field("vyvody", "Выводы", multiline=True),
            Field("predlozheniya", "Предложения / дальнейшие шаги", multiline=True),
            Field("rukovoditel", "Руководитель / кому представляется"),
        ),
    ),
    DocType(
        id="otchet_zaversheniya_programmy",
        title="Отчёт о завершении работы по программе",
        category="Отчёты",
        description="Краткий итоговый отчёт: программа закрыта, перечень результатов и акт передачи материалов.",
        filename="Otchet_zaversheniya_programmy.docx",
        fields=COMMON_ORG
        + (
            Field("programma", "Наименование программы / темы"),
            Field("fio", "Исполнитель"),
            Field("dolzhnost", "Должность"),
            Field("sroki", "Сроки"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("zadachi", "Поставленные задачи", multiline=True),
            Field("vypolneno", "Выполнено", multiline=True),
            Field("rezultaty", "Итоги", multiline=True),
            Field("peredano", "Что передано (файлы, записки, код)", multiline=True),
            Field("rukovoditel", "Принял / согласовал"),
        ),
    ),
    DocType(
        id="otchet_prodelannoy_raboty",
        title="Отчёт о проделанной работе",
        category="Отчёты",
        description="Итоговый/текущий отчёт о выполненных работах за период.",
        filename="Otchet_o_prodelannoy_rabote.docx",
        fields=COMMON_ORG
        + (
            Field("fio", "ФИО исполнителя"),
            Field("dolzhnost", "Должность"),
            Field("period", "Отчётный период"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("cel", "Цель / задача периода", multiline=True),
            Field("vypolneno", "Что выполнено (по пунктам)", multiline=True),
            Field("rezultaty", "Результаты / показатели", multiline=True),
            Field("problemy", "Проблемы / риски", multiline=True),
            Field("plany", "Планы на следующий период", multiline=True),
            Field("rukovoditel", "Руководитель (ФИО)"),
        ),
    ),
    DocType(
        id="otchet_po_proektu",
        title="Отчёт о результатах проекта",
        category="Отчёты",
        description="Отчёт по итогам проекта: цели, работы, результаты, выводы.",
        filename="Otchet_o_rezultatakh_proekta.docx",
        fields=COMMON_ORG
        + (
            Field("nazvanie", "Название проекта"),
            Field("fio", "Ответственный / автор отчёта"),
            Field("dolzhnost", "Должность"),
            Field("sroki", "Сроки проекта"),
            Field("data", "Дата отчёта", default="«____» ______________ 202__ г."),
            Field("cel", "Цель проекта", multiline=True),
            Field("zadachi", "Задачи", multiline=True),
            Field("vypolneno", "Выполненные работы", multiline=True),
            Field("rezultaty", "Достигнутые результаты", multiline=True),
            Field("produkty", "Продукты / артефакты (файлы, модули, документы)", multiline=True),
            Field("vyvody", "Выводы", multiline=True),
            Field("rekomendacii", "Рекомендации", multiline=True),
            Field("rukovoditel", "Руководитель проекта / согласующий"),
        ),
    ),
    DocType(
        id="otchet_za_period",
        title="Отчёт о результатах работы за период",
        category="Отчёты",
        description="Сводка результатов подразделения/сотрудника за месяц, квартал и т.п.",
        filename="Otchet_za_period.docx",
        fields=COMMON_ORG
        + (
            Field("fio", "ФИО"),
            Field("dolzhnost", "Должность"),
            Field("period", "Период (месяц / квартал / год)"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("pokazateli", "Ключевые показатели (название | план | факт)", multiline=True),
            Field("vypolneno", "Основные работы", multiline=True),
            Field("rezultaty", "Результаты", multiline=True),
            Field("vyvody", "Выводы", multiline=True),
            Field("rukovoditel", "Руководитель"),
        ),
    ),
    DocType(
        id="otchet_promezhutochnyy",
        title="Промежуточный отчёт по проекту",
        category="Отчёты",
        description="Статус проекта на дату: прогресс, блокеры, ближайшие шаги.",
        filename="Otchet_promezhutochnyy.docx",
        fields=COMMON_ORG
        + (
            Field("nazvanie", "Проект"),
            Field("fio", "Автор"),
            Field("dolzhnost", "Должность"),
            Field("data_statusa", "Дата статуса"),
            Field("progress", "Прогресс (% или этап)"),
            Field("sdelano", "Сделано с прошлого отчёта", multiline=True),
            Field("v_rabote", "В работе сейчас", multiline=True),
            Field("blockers", "Блокеры / риски", multiline=True),
            Field("next_steps", "Ближайшие шаги", multiline=True),
            Field("nuzhna_pomoshch", "Нужна помощь / решения", multiline=True),
            Field("rukovoditel", "Руководитель"),
        ),
    ),
    DocType(
        id="sluzhebnaya_zapiska",
        title="Служебная записка",
        category="Записки",
        description="Внутренняя служебная записка руководителю.",
        filename="Sluzhebnaya_zapiska.docx",
        fields=COMMON_ORG
        + (
            Field("komu", "Кому (должность, ФИО)"),
            Field("ot_kogo", "От кого (должность, ФИО)"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("tema", "Тема / о чём"),
            Field("tekst", "Текст записки", multiline=True),
            Field("prosba", "Просьба / предлагаю", multiline=True),
        ),
    ),
    DocType(
        id="dokladnaya_zapiska",
        title="Докладная записка",
        category="Записки",
        description="Докладная о факте, результате или проблеме.",
        filename="Dokladnaya_zapiska.docx",
        fields=COMMON_ORG
        + (
            Field("komu", "Кому"),
            Field("ot_kogo", "От кого"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("tema", "Тема"),
            Field("tekst", "Содержание", multiline=True),
            Field("vyvody", "Выводы / предложения", multiline=True),
        ),
    ),
    DocType(
        id="obyasnitelnaya",
        title="Объяснительная записка",
        category="Записки",
        description="Объяснение обстоятельств работнику.",
        filename="Obyasnitelnaya_zapiska.docx",
        fields=COMMON_ORG
        + (
            Field("komu", "Кому"),
            Field("fio", "ФИО работника"),
            Field("dolzhnost", "Должность"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("po_povodu", "По поводу"),
            Field("tekst", "Объяснение", multiline=True),
        ),
    ),
    DocType(
        id="resume_cv",
        title="Резюме (CV)",
        category="Карьера",
        description="Структурированное резюме для печати.",
        filename="Resume_CV.docx",
        fields=(
            Field("fio", "ФИО"),
            Field("dolzhnost_cel", "Желаемая должность"),
            Field("telefon", "Телефон"),
            Field("email", "E-mail"),
            Field("gorod", "Город", default="Минск"),
            Field("o_sebe", "Кратко о себе", multiline=True),
            Field("opyt", "Опыт работы (по строкам)", multiline=True),
            Field("obrazovanie", "Образование", multiline=True),
            Field("navyki", "Навыки (через запятую или с новой строки)", multiline=True),
            Field("yazyki", "Языки"),
        ),
    ),
    DocType(
        id="kharakteristika",
        title="Характеристика",
        category="Карьера",
        description="Характеристика с места работы.",
        filename="Kharakteristika.docx",
        fields=COMMON_ORG
        + (
            Field("fio", "ФИО характеризуемого"),
            Field("dolzhnost", "Должность"),
            Field("period", "Период работы"),
            Field("tekst", "Текст характеристики", multiline=True),
            Field("rekomendaciya", "Рекомендация", multiline=True),
            Field("rukovoditel", "Руководитель (ФИО, должность)"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
        ),
    ),
    DocType(
        id="akt_vypolnennyh_rabot",
        title="Акт выполненных работ",
        category="Акты",
        description="Акт сдачи-приёмки выполненных работ/услуг.",
        filename="Akt_vypolnennyh_rabot.docx",
        fields=COMMON_ORG
        + (
            Field("nomer", "№ акта"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("zakazchik", "Заказчик"),
            Field("ispolnitel", "Исполнитель"),
            Field("period", "Период выполнения"),
            Field("raboty", "Перечень работ (по строкам: работа | единица | кол-во | сумма)", multiline=True),
            Field("itogo", "Итого"),
            Field("primechanie", "Примечание", multiline=True),
        ),
    ),
    DocType(
        id="akt_priema_peredachi",
        title="Акт приёма-передачи",
        category="Акты",
        description="Передача имущества, документов, ТМЦ.",
        filename="Akt_priema_peredachi.docx",
        fields=COMMON_ORG
        + (
            Field("nomer", "№ акта"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("sdal", "Сдал (ФИО, должность)"),
            Field("prinyal", "Принял (ФИО, должность)"),
            Field("osnovanie", "Основание"),
            Field("perechen", "Перечень (по строкам)", multiline=True),
        ),
    ),
    DocType(
        id="akt_proverki",
        title="Акт проверки / обследования",
        category="Акты",
        description="Фиксация результатов проверки.",
        filename="Akt_proverki.docx",
        fields=COMMON_ORG
        + (
            Field("nomer", "№ акта"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("komissiya", "Состав комиссии", multiline=True),
            Field("obiekt", "Объект проверки"),
            Field("cel", "Цель"),
            Field("vyyavleno", "Выявлено", multiline=True),
            Field("zaklyuchenie", "Заключение", multiline=True),
        ),
    ),
    DocType(
        id="akt_spisaniya",
        title="Акт списания",
        category="Акты",
        description="Списание материалов / имущества (шаблон).",
        filename="Akt_spisaniya.docx",
        fields=COMMON_ORG
        + (
            Field("nomer", "№ акта"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("osnovanie", "Основание"),
            Field("komissiya", "Комиссия", multiline=True),
            Field("perechen", "К списанию (наименование | кол-во | причина)", multiline=True),
            Field("zaklyuchenie", "Заключение комиссии", multiline=True),
        ),
    ),
    DocType(
        id="zayavlenie_pk",
        title="Заявление о направлении на ПК",
        category="Повышение квалификации",
        description="Заявление о направлении на курсы / семинар.",
        filename="Zayavlenie_na_PK.docx",
        fields=COMMON_ORG
        + (
            Field("komu", "Кому"),
            Field("fio", "ФИО заявителя"),
            Field("dolzhnost", "Должность"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("programma", "Программа / курс"),
            Field("organizator", "Организатор"),
            Field("sroki", "Сроки"),
            Field("obosnovanie", "Обоснование", multiline=True),
        ),
    ),
    DocType(
        id="plan_pk",
        title="План повышения квалификации",
        category="Повышение квалификации",
        description="Индивидуальный / годовой план ПК.",
        filename="Plan_PK.docx",
        fields=COMMON_ORG
        + (
            Field("fio", "ФИО работника"),
            Field("dolzhnost", "Должность"),
            Field("god", "Год / период"),
            Field("cel", "Цель ПК", multiline=True),
            Field("meropriyatiya", "Мероприятия (дата | тема | форма | результат)", multiline=True),
            Field("rukovoditel", "Руководитель"),
        ),
    ),
    DocType(
        id="otchet_pk",
        title="Отчёт о повышении квалификации",
        category="Повышение квалификации",
        description="Отчёт по итогам обучения.",
        filename="Otchet_PK.docx",
        fields=COMMON_ORG
        + (
            Field("fio", "ФИО"),
            Field("dolzhnost", "Должность"),
            Field("programma", "Программа"),
            Field("sroki", "Сроки прохождения"),
            Field("gde", "Место / организатор"),
            Field("soderzhanie", "Что изучено", multiline=True),
            Field("primenenie", "Как применю на работе", multiline=True),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
        ),
    ),
    DocType(
        id="plan_nastavnichestva",
        title="План наставничества",
        category="Наставничество",
        description="План индивидуального наставничества (краткий комплектный шаблон).",
        filename="Plan_nastavnichestva.docx",
        fields=COMMON_ORG
        + (
            Field("prikaz", "Основание (приказ)", default="№ 154-ОД от 14.05.2026"),
            Field("nastavlyaemyj", "Наставляемый (ФИО, должность)"),
            Field("nastavnik", "Наставник (ФИО, должность)"),
            Field("rukovoditel", "Руководитель (ФИО)"),
            Field("period", "Период наставничества"),
            Field("cel", "Цель", multiline=True),
            Field("etapy", "Этапы (срок | содержание | результат)", multiline=True),
            Field("temy", "Темы (через запятую)", default="Python, Django, PostgreSQL, Oracle, нейронные сети"),
        ),
    ),
    DocType(
        id="zhurnal_nastavnichestva",
        title="Журнал наставничества",
        category="Наставничество",
        description="Журнал встреч наставник–наставляемый.",
        filename="Zhurnal_nastavnichestva.docx",
        fields=COMMON_ORG
        + (
            Field("prikaz", "Основание", default="№ 154-ОД от 14.05.2026"),
            Field("nastavlyaemyj", "Наставляемый"),
            Field("nastavnik", "Наставник"),
            Field("period", "Период"),
            Field("zapisi", "Записи (дата | тема | содержание | результат | задание)", multiline=True),
        ),
    ),
    DocType(
        id="zayavlenie_otpusk",
        title="Заявление (отпуск / день)",
        category="Заявления",
        description="Типовое заявление работника.",
        filename="Zayavlenie.docx",
        fields=COMMON_ORG
        + (
            Field("komu", "Кому"),
            Field("fio", "От кого (ФИО)"),
            Field("dolzhnost", "Должность"),
            Field("data", "Дата", default="«____» ______________ 202__ г."),
            Field("tekst", "Текст заявления", multiline=True, default="Прошу предоставить..."),
        ),
    ),
    DocType(
        id="protocol_soveshchaniya",
        title="Протокол совещания",
        category="Прочее",
        description="Краткий протокол рабочего совещания.",
        filename="Protokol_soveshchaniya.docx",
        fields=COMMON_ORG
        + (
            Field("nomer", "№ протокола"),
            Field("data", "Дата"),
            Field("tema", "Тема совещания"),
            Field("uchastniki", "Участники", multiline=True),
            Field("povestka", "Повестка", multiline=True),
            Field("resheniya", "Решения / поручения", multiline=True),
            Field("predsedatel", "Председатель"),
            Field("sekretar", "Секретарь"),
        ),
    ),
)


def get_doc_type(doc_id: str) -> DocType:
    for item in CATALOG:
        if item.id == doc_id:
            return item
    raise KeyError(doc_id)


def categories() -> list[str]:
    seen: list[str] = []
    for item in CATALOG:
        if item.category not in seen:
            seen.append(item.category)
    return seen
