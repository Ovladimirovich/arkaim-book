# Связи 119 сцен сценария с World Model и Knowledge Core

Отчёт формируется скриптом `scripts/generate_screenplay_world_links_report.py` из read-only каталога сцен `core/CORE/knowledge/screenplay_scene_catalog.py`.
Источники не изменяются; отчёт воспроизводим.

## 1. Что означают статусы связей

| Статус | Значение |
| --- | --- |
| `CONFIRMED` | Цель и её идентичность подтверждены владельцем: одобренная связь сценарий↔книга + одобренная claim-связь с валидной цепочкой до канонического события, либо точное совпадение имени персонажа с записью `characters_living` в World Model. |
| `DERIVED` | Связь вычислена по точному задокументированному правилу над существующими данными: идентификатор локации из `LOCATION_VISUALS` дословно совпал с `name_ru` локации World Model; дословное упоминание одобренной метки crosswalk; оба участника подтверждённой связи персонажей присутствуют в сцене; обогащение одобренного книжного чанка. |
| `UNRESOLVED` | Точного основания нет. Причина фиксируется явно, значение не подставляется. |
| `AMBIGUOUS` | На одну цель претендуют несколько сущностей. Выбор не выполняется, кандидаты перечисляются. |

## 2. Сводка

- Всего сцен: **119**
- Сцен с подтверждёнными связями: **93**
- Сцен с производными связями: **34**
- Сцен с неоднозначностями: **0**

| Тип связи | CONFIRMED | DERIVED | UNRESOLVED | AMBIGUOUS |
| --- | --- | --- | --- | --- |
| `book_entity` | 0 | 108 | 0 | 0 |
| `character` | 211 | 0 | 0 | 0 |
| `character_relation` | 0 | 30 | 0 | 0 |
| `epoch` | 6 | 0 | 0 | 0 |
| `event` | 6 | 0 | 9 | 0 |
| `location` | 0 | 1 | 118 | 0 |
| `location_mention` | 0 | 1 | 0 | 0 |
| **Итого связей** | 223 | 140 | 127 | 0 |

## 3. Пробелы (по типам отсутствующих связей)

| Тип | Сцен без связи |
| --- | --- |
| `book_entity` | 105 |
| `character` | 29 |
| `epoch` | 113 |
| `event` | 113 |
| `location` | 118 |

## 4. Неоднозначности

Неоднозначных связей не зафиксировано: ни одна локация/персонаж сцены не претендует сразу на несколько сущностей World Model.

## 5. Карта по всем 119 сценам

| Сцена | Заголовок | Confirmed | Derived | Unresolved | Ambiguous | Подтверждённые цели | Производные связи | Нет данных |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| scene_000 | 1. EXT. ГЛУБОКИЙ КОСМОС | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_001 | 2. EXT. МЛЕЧНЫЙ ПУТЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_002 | 3. EXT. СОЛНЕЧНАЯ СИСТЕМА | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_003 | 4. EXT. ЗЕМЛЯ | 0 | 6 | 2 | 0 | — | — | character, epoch, event, location |
| scene_004 | 5. EXT. КОСМОС | 2 | 7 | 1 | 0 | event:event_cosmic_impulse, epoch:pre_arkaim | — | character, location |
| scene_005 | 6. INT. ПЕЩЕРА | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_006 | 7. INT. ПЕЩЕРА | 0 | 7 | 2 | 0 | — | — | character, epoch, event, location |
| scene_007 | 8. INT. ПЕЩЕРА - ДЕНЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_008 | 9. INT. ПЕЩЕРА | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_009 | 10. INT. ПЕЩЕРА | 2 | 10 | 1 | 0 | event:event_cosmic_impulse, epoch:pre_arkaim | — | character, location |
| scene_010 | 11. INT. ПЕЩЕРА | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_011 | 12. INT. ПЕЩЕРА | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_012 | 13.EXT. ОКЕАН - ДЕНЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_013 | 14. EXT. ПРИГОРОД - ДЕНЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_014 | 15. EXT. ДОРОГА - ДЕНЬ | 1 | 6 | 2 | 0 | — | — | epoch, event, location |
| scene_015 | 16. EXT. ДОРОГА - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_016 | 17. EXT. УЧЕНИК В ДОРОГЕ - ДЕНЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_017 | 18. EXT. ТОТ ЖЕ. | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_018 | 19. EXT. ГЛОБАЛЬНЫЙ ВИД - ДЕНЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_019 | 20 EXT. ОСТРОВА АТЛАНТИДЫ - ДЕНЬ | 0 | 5 | 1 | 0 | — | location:атлантида | character, epoch, event |
| scene_020 | 21. EXT. ЖИЗНЬ НА ОСТРОВАХ - ДЕНЬ | 2 | 18 | 2 | 0 | event:event_oceania_decline, epoch:satya_yuga | — | character, location |
| scene_021 | 22.EXT. ОСТРОВА ОКЕАНИИ - ДЕНЬ | 0 | 10 | 2 | 0 | — | — | character, epoch, event, location |
| scene_022 | 23. INT. ШИКАРНЫЙ ЗАЛ - ДЕНЬ | 0 | 5 | 2 | 0 | — | — | character, epoch, event, location |
| scene_023 | 24. INT. КОМНАТА - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_024 | 25. EXT. ОТКРЫТОЕ ПРОСТРАНСТВО - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_025 | 26. EXT. БЕРЕГ - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_026 | 27. INT. СОВЕТ - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_027 | 28. INT. ЗАЛ - ДЕНЬ | 1 | 9 | 2 | 0 | — | — | epoch, event, location |
| scene_028 | 29. INT. ЗАЛ - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_029 | 30. INT. ЗАЛ - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_030 | 31. EXT. БАЛКОН - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_031 | 32. EXT. ЛЕТНОЕ ПОЛЕ - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_032 | 33. EXT. ЛЕТНОЕ ПОЛЕ - ДЕНЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_033 | 34. INT. КАБИНА АЭРОЛЕТА - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_034 | 35. EXT. ВОЗДУШНОЕ ПРОСТРАНСТВО - НОЧЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_035 | 36. EXT. ПРИЗЕМЛИВШИЙСЯ АЭРОЛЕТ - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_036 | 37. EXT. ПЛАТО - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_037 | 38. EXT. ОТКРЫТОЕ ПРОСТРАНСТВО - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_038 | 39. EXT. У ДОМИКА - ВЕЧЕР | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_039 | 40. INT. ДОМИК - ВЕЧЕР | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_040 | 41. INT. ЗАЛ В ДОМЕ - ВЕЧЕР | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_041 | 42. МОНТАЖ - ОБУЧЕНИЕ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_042 | 43. EXT. ПОДХОД К ГОРОДУ - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_043 | 44. EXT. УЛИЦА ГОРОДА - ДЕНЬ | 3 | 1 | 1 | 0 | — | character_relation:Учитель mentor_of Велик | book_entity, epoch, event, location |
| scene_044 | 45. EXT. УЛИЦА ГОРОДА - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_045 | 46. INT. КОМНАТА - ДЕНЬ | 4 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_046 | 47. MONTAGE - ЭПИЗОДЫ ИЗ ЖИЗНИ ВЕРЫ И В… | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_047 | 48. MONTAGE - ОЗНАКОМЛЕНИЕ С БЫТОМ И МИ… | 2 | 4 | 2 | 0 | — | — | epoch, event, location |
| scene_048 | 49. INT. ДОМ - ДЕНЬ | 5 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_049 | 50. INT. ЗАЛ - ДЕНЬ | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_050 | 51. INT. ЗАЛ - ДЕНЬ | 3 | 1 | 1 | 0 | — | character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_051 | 52. EXT. ГОРОД - ЗАКАТ | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_052 | 53. INT. КОМНАТА ВЕЛИУСМУСА - НОЧЬ | 3 | 1 | 1 | 0 | — | character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_053 | 54. INT. ЗАЛ - ДЕНЬ | 4 | 3 | 1 | 0 | — | character_relation:Учитель mentor_of Велик, character_relation:Световит mentor_of Велик, character_relation:Учитель mentor_of Наставники | book_entity, epoch, event, location |
| scene_054 | 55. EXT. УЛИЦА - ДЕНЬ | 3 | 1 | 1 | 0 | — | character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_055 | 56. INT. КОМНАТА ВЕЛИУСМУСА - ВЕЧЕР | 2 | 1 | 1 | 0 | — | character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_056 | 57. EXT. ТРОПИНКА - ДЕНЬ | 3 | 1 | 1 | 0 | — | character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_057 | 58. EXT. ВОЗЛЕ ДОМА - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_058 | 59. INT. КОМНАТА -УТРО | 3 | 1 | 1 | 0 | — | character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_059 | 60.INT. КОМНАТА ВЕЛА - ВЕЧЕР | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_060 | 60.INT. ЗАЛ - УТРО | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_061 | 61.INT. ДОРГА - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_062 | 62.INT. УСАДЬБА - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_063 | 63.EXT. ДОРГА - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_064 | 64.EXT. ПРИВАЛ - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_065 | 65.EXT. ДОРГА - ДЕНЬ | 3 | 1 | 1 | 0 | — | character_relation:Учитель mentor_of Велик | book_entity, epoch, event, location |
| scene_066 | 66.EXT. ПРИРОДА - ДЕНЬ | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_067 | 67. EXT. ДОРГА - ДЕНЬ | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_068 | 68.EXT. ПАНОРАМА ГОРОДА - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_069 | 69.INT. КОМНАТА - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_070 | 70.INT. КОМНАТА ВЕЛА - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_071 | 71.INT. КОМНАТА ВЕЛА - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_072 | 72.EXT. ГОРОД – ДЕНЬ | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_073 | 73.INT. КОМНАТА СЛАВНОГО – НОЧЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_074 | 74.EXT. | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_075 | 75.INT. КОМНАТА ВЕЛА - ДЕНЬ. ВЕЛ МЕДИТИ… | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_076 | 76.INT. КОМНАТА ВЕЛА - НОЧЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_077 | 77.EXT. ПРОСТРАНСТВО - МОНТАЖ | 4 | 2 | 1 | 0 | — | character_relation:Учитель mentor_of Велик, character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_078 | 78.ВНУТРЕННИЙ ЗАЛ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_079 | 79.INT. ПУТЬ - ДЕНЬ | 4 | 2 | 1 | 0 | — | character_relation:Учитель mentor_of Велик, character_relation:Учитель mentor_of Наставники | book_entity, epoch, event, location |
| scene_080 | 79.INT. ЦЕНТРАЛЬНОЕ ЗДАНИЕ - ДЕНЬ | 4 | 1 | 1 | 0 | — | character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_081 | 80.INT. ЦЕНТРАЛЬНОЕ ЗДАНИЕ | 6 | 12 | 1 | 0 | event:event_kali_yuga_onset, epoch:эпоха_кали_юги | — | location |
| scene_082 | 80.EXT.ГОРЫ.СМЕНА ЛАНДШАФТА | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_083 | 81.EXT.ГОРЫ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_084 | 82.EXT.Горная тропа, перевал. | 4 | 3 | 1 | 0 | — | character_relation:Учитель mentor_of Велик, character_relation:Световит mentor_of Велик, character_relation:Учитель mentor_of Наставники | book_entity, epoch, event, location |
| scene_085 | 83. EXT. В колонне переселенцев. | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_086 | 84.EXT. ПРИРОДА .ВЕЧЕР | 5 | 5 | 1 | 0 | event:event_kali_yuga_onset, epoch:эпоха_кали_юги | — | location |
| scene_087 | 85.EXT.Временный лагерь, | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_088 | 86.INT.Комната. В ней — Славный, Велики… | 6 | 1 | 1 | 0 | — | character_relation:Радомир peer_of Велик | book_entity, epoch, event, location |
| scene_089 | 86.EXT. (Переселенцы выходят из лагеря. | 5 | 2 | 1 | 0 | — | character_relation:Световит mentor_of Велик, character_relation:Радомир peer_of Велик | book_entity, epoch, event, location |
| scene_090 | 87.EXT.Серия сюжетов: Радомир и мужчина… | 7 | 3 | 1 | 0 | — | character_relation:Учитель mentor_of Велик, character_relation:Световит mentor_of Велик, character_relation:Радомир peer_of Велик | book_entity, epoch, event, location |
| scene_091 | 88. EXT.ДОЛИНА.ПРИГОРОК.СМЕРКАЕТСЯ. | 4 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_092 | 89.EXT.РАВНИНА. НОЧЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_093 | 90. EXT. УСКОРЕННАЯ СЪЁМКА - ПРИВАЛ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_094 | 91. EXT. СТРОИТЕЛЬСТВО ГОРОДКА | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_095 | 92.EXT. ЛЕС И МЕДИТАЦИЯ НАСТАВНИКОВ | 2 | 1 | 1 | 0 | — | character_relation:Учитель mentor_of Наставники | book_entity, epoch, event, location |
| scene_096 | 93.EXT. ИЛЛЮЗОРНЫЙ КАРКАС ГОРОДКА форми… | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_097 | 93.EXT. ЛАГЕРЬ - ДЕНЬ | 4 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_098 | 94. EXT. СЦЕНА ПЕРЕХОДИТ В ОБЩИЙ ПЛАН С… | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_099 | 95.ИНТ. ДОМ - ДЕНЬ | 7 | 2 | 1 | 0 | — | character_relation:Световит mentor_of Велик, character_relation:Радомир peer_of Велик | book_entity, epoch, event, location |
| scene_100 | 96. ЭКСТ. ГОРОДОК - ДЕНЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_101 | 97. EXT. В ДРУГОМ ГОРОДКЕ ОЖИВЛЕННОЕ ДВ… | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_102 | 98. ИНТ. СТРОЕНИЕ - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_103 | 99.EXT. МЕСТНОСТЬ - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_104 | 100.INT. ДОМА - ДЕНЬ | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_105 | 101.EXT. Общий вид городка √3. План мес… | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_106 | 102.EXT. Сцены с медитирующими наставни… | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_107 | 103.EXT. ЦЕНТРАЛЬНАЯ ПЛОЩАДЬ ГОРОДКА √1… | 5 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_108 | 104.EXT. УЛИЦА - ДЕНЬ | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_109 | 105.EXT. | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_110 | 106. EXT. МЕСТНОСТЬ - ДЕНЬ | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_111 | 107.INT. КОМНАТА ВЕЛИКА - ДЕНЬ | 3 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_112 | 108.INT. ЖИВОПИСНОЕ МЕСТО - ДЕНЬ | 5 | 2 | 1 | 0 | — | character_relation:Учитель mentor_of Велик, character_relation:Световит mentor_of Велик | book_entity, epoch, event, location |
| scene_113 | 109.EXT | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_114 | 110.EXT. ДОРЕГА - ДЕНЬ | 2 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_115 | 111.EXT На горизонте появляется городок. | 0 | 0 | 1 | 0 | — | — | book_entity, character, epoch, event, location |
| scene_116 | 112.EXT. Они входят в городок, вокруг н… | 1 | 0 | 1 | 0 | — | — | book_entity, epoch, event, location |
| scene_117 | 113.EXT. Они заходят в город. Городок С… | 6 | 5 | 1 | 0 | event:event_awakening, epoch:переход_к_новой_эре_(кали_юга) | — | location |
| scene_118 | INT. ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ | 0 | 1 | 1 | 0 | — | location_mention:аркаим | book_entity, character, epoch, event, location |

## 6. Наблюдения по качеству данных (требуют решения владельца)

- **Локации сцен почти не сопоставимы с миром.** 118 из 119 сцен не имеют точного соответствия: заголовки сценария — это общие места действия (`ПЕЩЕРА`, `ЗАЛ`, `КОМНАТА`), а не имена локаций мира. Сопоставление по падежным формам небезопасно: в тексте преобладает `Гипербореи` (люди) при `Гиперборея` (место) — основа отличается одной буквой.
- **Точное упоминание одобренной метки crosswalk** даёт 1 связь: упоминание помечается отдельно от места действия сцены.
- **`Океания` не имеет одобренного соответствия** в World Model: в `LOCATION_VISUALS` ключ есть, в `WORLD_MODEL.json` локации нет, в crosswalk одобрений нет. Требуется решение владельца: одобрять ли `region_oceania`.
- **В `WORLD_MODEL.json` есть дубли локаций и персонажей**: `аркаим`/`arkaim` и `гиперборея`/`hyperborea` описывают одну сущность разными идентификаторами; персонажи присутствуют одновременно как `Славный`, `Мирослав` и `Мирослав (Славный)`. Связи строятся только по точному совпадению имени, поэтому дубли не склеиваются.
- **Канонический персонаж `Ученики`** в мире записан как `Ученики (плеяда)`. Точного совпадения нет, поэтому персонаж в сценах с упоминанием «ученики» не связывается с миром и остаётся в статусе `UNRESOLVED`.
- **События и эпохи** доступны только через одобренную цепочку `screenplay_links.json` → `claim_temporal_links.json` → `WORLD_MODEL.json`: 6 сцен имеют подтверждённое событие и эпоху; 9 сцен с одобренной книжной связью (всего сцен с книжной связью — 14) не имеют подтверждённой claim-связи и остаются `UNRESOLVED`.

## 7. Источники

- `core/KNOWLEDGE/screenplay_links.json` — одобренные связи сценарий↔книга (15).
- `core/KNOWLEDGE/claim_temporal_links.json` — одобренные связи claim→событие/эпоха (9).
- `core/KNOWLEDGE/enriched_chunks.json` — тексты книжных чанков и их обогащение.
- `core/CORE/narrative_engine/data/WORLD_MODEL.json` — эпохи, локации, персонажи, события.
- `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json` — одобренные соответствия (2).
- `core/CORE/visual/VISUAL_KNOWLEDGE/LOCATION_VISUALS.json` — ключи визуальных локаций.

