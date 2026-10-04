# AI-LC a AWS `aidlc-workflows`: porównanie i możliwe kierunki rozwoju

**Stan przeglądu:** 2026-10-04
**Zakres:** publiczna dokumentacja i struktura `awslabs/aidlc-workflows` na gałęzi `main`, porównane z kodem i dokumentacją AI-LC na `origin/develop`. To analiza możliwości, nie decyzja o wdrożeniu ani obietnica zgodności z metodologią AWS.

## Wniosek w skrócie

Oba projekty stosują podobną zasadę podziału odpowiedzialności: deterministyczny rdzeń prowadzi przepływ, a harness dostarcza zachowanie modelu i narzędzia. Cele są jednak różne. AWS AI-DLC organizuje wytwarzanie i utrzymanie oprogramowania, podczas gdy AI-LC prowadzi naukę i dopuszcza postęp wyłącznie na podstawie dowodów. Nie należy kopiować jego etapów dostarczania oprogramowania ani dodatkowych ról wprost.

AI-LC ma już kluczowe odpowiedniki: niezależne role Master i pięciu specjalistów, profil kursu uzgadniany z uczącym się, fazowe briefy, bramki oparte na dowodach, deterministyczny silnik, zapis zdarzeń oraz eksport stanu. Największa przestrzeń do poprawy leży w konfigurowalności tego, jak te części są składane, w przenośności między harnessami i w długoterminowym zarządzaniu kursem.

| Obszar | Stan w AI-LC | Możliwy kierunek | Priorytet |
| --- | --- | --- | --- |
| Konfigurowalne ścieżki i profile uczenia | Profile określają cel, poziom, głębokość i diagnozowane kompetencje; fazy i reguły przejść są w dużej mierze stałe w silniku | Deklaratywne, walidowane profile przebiegu kursu, które wybierają dozwolone fazy i ich ustawienia, bez katalogu gotowych ćwiczeń | Wysoki |
| Punkty kontrolne i zgody | Zgoda na profil jest częścią rozmowy i konfiguracji; briefy i dowody trafiają do historii | Jawny, trwały punkt zatwierdzenia planu lub istotnej zmiany kursu, z możliwością korekty przez uczącego się | Wysoki |
| Obsługa harnessów | Są instrukcje i umiejętności `.agents/skills`; bieżąca integracja jest opisana głównie dla Codex | Adaptery i jawny kontrakt funkcji dla wielu harnessów oraz wspólny zestaw testów zgodności | Wysoki |
| Ewolucja istniejących kursów | Snapshot zachowuje kopie pakietów, ale nie ma migracji schematu ani bezpiecznej aktualizacji programu w miejscu | Wersjonowane migracje i kontrolowany podgląd zmian do istniejących kursów | Średni/wysoki |
| Historia decyzji dydaktycznych | Jest historia briefów i dowodów oraz możliwość eksportu stanu | Powiązać ważne decyzje Mastera i zmiany planu z ich podstawą oraz rewizją profilu, z ochroną prywatności | Średni |
| Rozszerzenia walidacji | Istnieją czujniki deterministyczne i protokoły danych | Rozszerzalny, ściśle typowany interfejs czujników/warunków, bez wykonywania kodu uczącego się | Średni |

## Czym jest porównywany projekt

AWS opisuje AI-DLC jako metodologię kierującą pracą asystentów programistycznych przez cykl tworzenia oprogramowania. Publiczne README wymienia pięć faz i 33 etapy, 14 ról, 11 profili przebiegu, zatwierdzenia człowieka, audyt zdarzeń i obsługę kilku harnessów. Konfiguracja jest rozdzielona między neutralny rdzeń, integracje harnessów, profile/etapy i narzędzia pakujące. [README projektu](https://github.com/awslabs/aidlc-workflows), [Workflow Profiles](https://github.com/awslabs/aidlc-workflows/blob/main/docs/guide/workflow-profiles.md), [Harness Engineer Guide](https://github.com/awslabs/aidlc-workflows/blob/main/docs/harness-engineering/00-overview.md)

Profile AWS wybierają trasę etapów, poziom szczegółowości, strategię testów, pułap przeglądów i część ustawień formalności. Projekt oferuje zarówno profile ogólne, jak i wąskie, np. poprawkę błędu, refaktoryzację, infrastrukturę czy warsztat. Złożony przebieg może zostać skomponowany, ale przed utworzeniem wymaga zatwierdzenia. Etapy i role są osobnymi pojęciami, a wiele rozszerzeń metodologii można zadeklarować w danych konfiguracyjnych zamiast zmieniać kod silnika. [Workflow Profiles](https://github.com/awslabs/aidlc-workflows/blob/main/docs/guide/workflow-profiles.md), [Harness Engineer Guide](https://github.com/awslabs/aidlc-workflows/blob/main/docs/harness-engineering/00-overview.md)

## Porównanie zdolności

| Zdolność | AWS AI-DLC | AI-LC | Ocena dla AI-LC |
| --- | --- | --- | --- |
| Główny cel | Weryfikowalne dostarczanie i utrzymanie oprogramowania | Adaptacyjne uczenie techniczne, kompetencje i trwałość wiedzy | Różne domeny; metody procesowe trzeba mapować na naukę, nie kopiować |
| Podział rdzeń–model | Rdzeń/harness kieruje procesem; wybrany harness zapewnia model i narzędzia | Python waliduje, planuje, utrzymuje graf, bramki i zapis; zewnętrzny harness naucza, generuje ćwiczenia i ocenia semantycznie | Silna zgodność architektoniczna już istnieje |
| Role | 14 ról, w tym eksperci, recenzenci i composer | Master plus pięć ról specjalistycznych | Własny zestaw ról jest świadomym wyborem; nie ma potrzeby dodawać ról AWS |
| Przebiegi pracy | Wybieralne i komponowalne profile sterują trasą etapów, głębokością i kontrolami | Zakresy sesji (np. nauka, powtórka, remediacja) oraz profile ucznia; główna maszyna faz jest określona w `engine.py` | Brakuje użytkowej konfiguracji pełnej trasy i jej parametrów, nie samego routingu |
| Punkty kontroli | Zgody człowieka zatrzymują proces w określonych bramkach; decyzje są częścią przebiegu | Intake blokuje planowanie do zebrania diagnozy; dowody i bramki blokują mastery | AI-LC ma silne bramki merytoryczne; warto rozważyć jawne zgody na zmianę planu, nie dodatkową zgodę na każde ćwiczenie |
| Audyt i pamięć | Trwały stan, zarejestrowane decyzje i rozbudowany dziennik zdarzeń; pamięć/poznane reguły | Atomowy snapshot oraz historia briefów i dowodów, `history`, eksport i `doctor` | Fundament jest; brakującą wartością może być pochodzenie zmian planu i ich wersjonowanie |
| Rozszerzanie metodologii | Etapy, role, zakresy, reguły, czujniki i wiedza konfigurowane deklaratywnie | Walidowane YAML pakietów domen oraz provider protocols; silnik, profile i większość polityki są w kodzie/instrukcjach | Rozszerzyć ostrożnie o deklaratywne warianty przebiegu i kontrakty rozszerzeń |
| Harnessy | Wspólny rdzeń z opisanymi integracjami m.in. Codex, Claude Code, Kiro, Cursor, opencode i Copilot | Skille są odkrywalne w `.agents/skills`; launcher i obecne instrukcje są dopracowane dla bieżącego użycia, lecz brak kompletnej macierzy harnessów | Duża szansa na poprawę dostępności, przy zachowaniu niezależności od dostawcy |
| Rozwój istniejącego stanu | Narzędzia konfiguracji/naprawy i jawna obsługa stanu workflow | Nieobsługiwane migracje schematu i aktualizacja pakietów w skonfigurowanym kursie; niezgodność kończy się błędem | Ważny kierunek po ustabilizowaniu schematów i reguł zgodności |
| Bezpieczeństwo wykonania | Reguły dostępu i narzędzia określane przez harness/stage | AI-LC nie uruchamia kodu ucznia; waliduje AST i dane liczbowo; wykonanie wymaga prawdziwego zewnętrznego sandboxa | Obecna granica jest celowa i powinna pozostać nienaruszona |

## Proponowane prace

Szacunki wysiłku są względne: **S** — niewielka zmiana dokumentacji/modelu, **M** — nowy kontrakt i integracja z CLI/snapshotem, **L** — zmiana przekrojowa wymagająca migracji lub kilku adapterów. Priorytety nie są zatwierdzonym planem wydania.

| ID | Propozycja | Co dziś ogranicza AI-LC | Możliwy kształt implementacji | Korzyść i ryzyko | Wysiłek / priorytet |
| --- | --- | --- | --- | --- | --- |
| R1 | Deklaratywne profile przebiegu nauki | `LearningProfile` wybiera cel i głębokość; decyzje fazowe i trasy są w `engine.py` | Dodać osobny, wersjonowany `LearningPathProfile`: np. `focused`, `balanced`, `project-led`; walidować dozwolone fazy, proporcje ćwiczeń/projektów, reguły powtórek i warunki pominięcia. Silnik nadal odrzuca trasę, która omija diagnozę, prerequisite closure, dowody, remediację lub opóźnione sprawdzenie. | Umożliwia dopasowanie formalności i rytmu do celu. Ryzyko: profil nie może zmniejszać standardu dowodów ani tworzyć sztywnej kolejności ćwiczeń. | M / wysoki |
| R2 | Zatwierdzany plan i kontrolowane zmiany | Uzgodniony profil i intake istnieją, ale zapis nie rozróżnia stanu „plan przedstawiony” od „plan zaakceptowany” jako osobnej decyzji | Dodać typowany obiekt planu z wersją i streszczeniem; zdarzenia `plan.proposed`, `plan.approved`, `plan.revised`; wymagać zgody tylko przy utworzeniu kursu lub istotnej zmianie celu/tras. Zachować bieżące krótkie briefy sesji bez dodatkowych dialogów zatwierdzających. | Uczący się rozumie wpływ zmiany zakresu i zachowuje kontrolę. Ryzyko: nadmierne prośby o akceptację utrudnią naukę; zdefiniować, co jest zmianą istotną. | M / wysoki |
| R3 | Kontrakt harnessów i testy zgodności | AI-LC dostarcza umiejętności/instrukcje dla harnessu, ale nie ma formalnej deklaracji wspólnych funkcji ani macierzy testów | Zdefiniować manifest capabilities (odkrywanie skill, uruchamianie lokalnego CLI, pliki/artefakty, izolowana ocena, media, sandbox); napisać adaptery instrukcji bez logiki biznesowej; zbudować test fixture, który sprawdza, czy każdy adapter przekazuje te same briefy i wymagane dane Assessorowi. | Więcej środowisk pracy i mniejsze rozjeżdżanie się instrukcji. Ryzyko: utrzymywanie wielu wariantów oraz testowanie zachowań modelu; zacząć od kontraktu statycznego i testów protokołu. | M–L / wysoki |
| R4 | Bezpieczna migracja i aktualizacja kursu | Snapshot chroni przed cichą zmianą pakietu, lecz nie ma migracji schematu ani aktualizacji pakietów w aktywnym kursie | Dodać jawne `snapshot_version`, migracje krok po kroku i polecenie diagnostyczne/preview. Migracja kopii kursu powinna wykazać różnice grafu i rubryk, zachować dowody i historię, wykrywać usunięte kompetencje i zatrzymywać się przy nierozstrzygniętych mapowaniach. | Utrzymanie kursów między wydaniami bez ręcznego przepisywania stanu. Ryzyko: błędne przeniesienie dowodów na zmienione znaczenie kompetencji; mapowanie nie może być automatyczne bez równoważności. | L / średni-wysoki |
| R5 | Historia decyzji i pochodzenie planu | Historia pokazuje sesje/evidence, ale zmiana założeń, przypisanie planu i jego źródła mogą być mniej widoczne niż sam wynik ucznia | Rozszerzać istniejące zdarzenia o identyfikator profilu i rewizji, powód routingu, kompetencje wejściowe, odwołane dowody i jawne źródła. Zapewnić redakcję danych osobowych; nie archiwizować pełnych rozmów domyślnie. | Łatwiejszy przegląd błędów routingu i wyjaśnienie, dlaczego pojawiło się dane zadanie. Ryzyko: nadmierne utrwalanie wrażliwych wypowiedzi. | S–M / średni |
| R6 | Rozszerzenia czujników z ograniczonym kontraktem | Czujniki są deterministyczne, lecz nowe kontrole wymagają rozbudowy kodu | Wprowadzić rejestr nazwanych, typowanych kontroli i deklaratywnych warunków na już obsługiwanych danych (kształt, skończoność, jednostki, dostępność, podział); nie dopuszczać wykonywalnych pluginów ani kodu kursu. | Łatwiej dodawać kontrole specyficzne dla dziedziny przy zachowaniu audytowalności. Ryzyko: fałszywe poczucie semantycznej oceny; sensor nigdy nie zastępuje niezależnego Assessora. | M / średni |
| R7 | Ustandaryzowany lifecycle sesji | Są fazy i briefy sesji, ale wynik nauki, zamknięcie sesji i plan następnego kontaktu nie są pełnym, jawnie konfigurowalnym protokołem workflow | Rozważyć lekki protokół rozpoczęcie → praca → synteza → zapis dowodów → następny krok, z warunkami wejścia/wyjścia i możliwością przerwania/wznowienia. Wykorzystywać istniejące review scheduling, nie tworzyć drugiego mechanizmu nauki. | Bardziej czytelne podsumowania i ciągłość między sesjami. Ryzyko: dublowanie obecnego silnika lub narzucenie zbędnej ceremonii; najpierw zweryfikować lukę na przykładach. | S–M / niski/średni |

## Proponowana kolejność

| Etap | Zakres | Warunek przejścia |
| --- | --- | --- |
| 1. Doprecyzowanie kontraktów | Uzgodnić definicję „istotnej zmiany planu”, capabilities harnessu i granice danych utrwalanych w historii | Przykładowe scenariusze pokazują brak dublowania evidence gates, `LearningProfile` i `history` |
| 2. Mały prototyp R1 + R2 | Jeden profil przebiegu i wersjonowana propozycja planu z akceptacją; bez nowych ról i bez statycznego banku ćwiczeń | Testy potwierdzają, że żaden profil ani akceptacja nie omija baseline, zależności, niezależnej oceny, hint gates, regresji i powtórek |
| 3. Kontrakt harnessu | Opisać wspólny protokół i capability manifest, dodać drugi adapter jako dowód przenośności | Ten sam scenariusz dostarcza równoważne briefy i dane dla Assessorów w obu harnessach |
| 4. Migracje | Najpierw formalnie wersjonować snapshoty i pakiety, potem testować migrację kopii prawdziwych wersji | Dowody, audyt i pliki ucznia pozostają spójne; niejednoznaczne mapowania przerywają migrację bez utraty danych |
| 5. Rozszerzenia i ergonomia | Rozszerzyć czujniki albo lifecycle sesji tylko tam, gdzie scenariusze wykazały realną potrzebę | Każdy nowy interfejs pozostaje deterministyczny, testowalny i bezpieczny dla danych ucznia |

## Poza zakresem na teraz

| Pomysł z AWS, którego nie kopiować wprost | Powód |
| --- | --- |
| Fazy Ideation, Inception, Construction, Operations oraz etapy budowania produktu | To model wytwarzania oprogramowania; AI-LC ma model diagnozy, nauki, utrwalania i transferu |
| 14-osobowa taksonomia ról | AI-LC ma ustalony Master plus pięć specjalistycznych ról; rozbudowa ról nie jest sama w sobie korzyścią i może osłabić niezależność Assessora |
| „Mniej formalny” profil, który osłabia standardy | Tryb krótszej ścieżki nie może osłabiać prerequisite closure, niezależnych dowodów, obsługi błędów ani bramek mastery |
| Ogólne wykonanie skryptów/pluginów | AI-LC nie dostarcza sandboxa; nie wolno interpretować danych profilu jako bezpiecznego kodu wykonywalnego |
| Rozbudowana telemetria rozmów | Dane ucznia mogą być wrażliwe; wystarczą minimalne decyzje i pochodzenie dowodu, jeśli mają jasny cel i retencję |

## Źródła i podstawa porównania

- [Repozytorium AWS `aidlc-workflows`](https://github.com/awslabs/aidlc-workflows) — opis celu, faz, ról, profili, harnessów i układu repozytorium.
- [Workflow Profiles](https://github.com/awslabs/aidlc-workflows/blob/main/docs/guide/workflow-profiles.md) — trasy, głębokość, testy, ograniczenia przeglądu oraz komponowanie przebiegu.
- [Harness Engineer Guide](https://github.com/awslabs/aidlc-workflows/blob/main/docs/harness-engineering/00-overview.md) — rozdział stage/agent oraz konfigurowanie zakresów, reguł, sensorów i wiedzy.
- [AI-DLC Workflows 2.0 Specification](https://github.com/awslabs/aidlc-workflows/blob/main/assets/AI-DLC-Workflows-2.0-Specification.pdf) — specyfikacja metodologii linkowana z README projektu.
- Lokalne odniesienia AI-LC: [`docs/architecture.md`](architecture.md), [`docs/agent-model.md`](agent-model.md), [`docs/domain-authoring.md`](domain-authoring.md), [`README.md`](../README.md), `src/ailearn/engine.py`, `src/ailearn/models.py`, `src/ailearn/store.py`.

Repozytorium AWS jest rozwijane na `main`; opisy mogą się zmienić. Powyższe liczby i funkcje odzwierciedlają stronę projektu sprawdzoną w dniu przeglądu. Przed podjęciem decyzji implementacyjnej należy ponownie sprawdzić aktualne źródła i zweryfikować rekomendacje na rzeczywistych scenariuszach uczenia AI-LC.
