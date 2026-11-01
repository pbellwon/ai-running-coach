"""Deterministic calendar planning; no predicted race times or automatic acceptance."""
from collections import defaultdict
from datetime import date, timedelta
import math

from app.engine.existing_plan_importer import ExistingPlanImporter
from app.engine.planned_workout_engine import PlannedWorkoutEngine
from app.services.coach_chat_service import ChatError

PLAN_COLUMNS = ExistingPlanImporter.REQUIRED_COLUMNS
MARKER = '\n\nObowiązujący trening po korekcie PaceMind:\n'
RACE_COLUMNS = {'date', 'name', 'distance_km', 'priority', 'target_time', 'notes'}


def number(value):
    try:
        result = float(str(value).replace(',', '.'))
        if not math.isfinite(result) or result < 0:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise ChatError(422, 'Dystanse i czasy w arkuszu muszą być nieujemnymi liczbami.')


def parse_calendar(snapshot):
    if not RACE_COLUMNS.issubset(snapshot['headers']):
        raise ChatError(422, 'race_calendar wymaga kolumn: date, name, distance_km, priority, target_time, notes.')
    events, seen = [], set()
    for index, row in enumerate(snapshot['rows'], 2):
        if not any(str(v).strip() for v in row.values()):
            continue
        try:
            day = date.fromisoformat(row.get('date', '').strip())
        except ValueError:
            raise ChatError(422, f'race_calendar, wiersz {index}: data musi mieć format YYYY-MM-DD.')
        priority = row.get('priority', '').strip().upper()
        name = row.get('name', '').strip()
        distance = number(row.get('distance_km', ''))
        if not name or len(name) > 200 or priority not in ('A', 'B', 'C') or not 0 < distance <= 100:
            raise ChatError(422, f'race_calendar, wiersz {index}: podaj nazwę, dystans 0–100 km i priorytet A/B/C.')
        if day in seen:
            raise ChatError(422, f'race_calendar: więcej niż jeden start w dniu {day}. Rozstrzygnij wybór startu.')
        seen.add(day)
        target = row.get('target_time', '').strip()
        if target:
            parts = target.split(':')
            if (len(parts) not in (2, 3) or not all(p.isdigit() for p in parts)
                    or any(int(p) >= 60 for p in parts[1:]) or sum(int(p) for p in parts) == 0):
                raise ChatError(422, f'race_calendar, wiersz {index}: target_time to MM:SS lub HH:MM:SS.')
        events.append({'date': day.isoformat(), 'name': name, 'distance_km': distance,
                       'priority': priority, 'target_time': target, 'notes': row.get('notes', '')})
    return sorted(events, key=lambda e: e['date'])


def recovery_days(event):
    distance = event['distance_km']
    return 10 if distance > 42.2 else 7 if distance > 21.1 else 4 if distance > 10 else 2


class RacePlanEngine:
    """Apply an evidence-based ten-day microcycle to the calendar, preserving audit data."""
    def build(self, snapshot, events, strategy, start, end, replace, protected_rows, today, limits):
        if not PLAN_COLUMNS.issubset(snapshot['headers']):
            raise ChatError(422, 'plan_import nie ma wymaganych dotychczasowych kolumn.')
        if start <= today or end < start or (end-start).days > 365 or (start-today).days > 30:
            raise ChatError(422, 'Początek musi być od jutra do 30 dni naprzód; plan może obejmować najwyżej 366 dni.')
        selected = [e for e in events if start.isoformat() <= e['date'] <= end.isoformat()]
        if not any(e['priority'] == 'A' for e in selected):
            raise ChatError(422, 'W okresie planu musi być przynajmniej jeden start główny A.')
        rows_by_date = defaultdict(list)
        for index, row in enumerate(snapshot['rows'], 2):
            if not any(str(v).strip() for v in row.values()):
                continue
            try:
                day = date.fromisoformat(row.get('date', ''))
            except ValueError:
                raise ChatError(422, f'plan_import, wiersz {index}: nieprawidłowa data.')
            rows_by_date[day].append((index, row))
        preserved = {d: entries for d, entries in rows_by_date.items() if start <= d <= end and
            (not replace or len(entries) > 1 or any(i in protected_rows or self._protected_description(r['description']) for i, r in entries))}
        warnings, blockers, entries, cycles = [], [], [], []
        by_date = {date.fromisoformat(e['date']): e for e in events}
        for d, old in preserved.items():
            if d in by_date:
                distance = sum(number(r['planned_distance_km'] or 0) for _, r in old)
                if not any(self._type(r) == 'race' for _, r in old) or abs(distance-by_date[d]['distance_km']) > .2:
                    blockers.append(f'{d}: chroniony lub zachowany trening nie odpowiada zawodom. Skoryguj tę jednostkę osobno.')
        pattern = {d['offset']: d for d in strategy['days']}
        anchor = start - timedelta(days=strategy['start_offset'])
        base_km = sum(d['distance_km'] for d in pattern.values())
        hard_dates = [d for d, old in rows_by_date.items() if d in preserved or d < start or d > end
                      if any(self._type(r) not in ('off', 'easy_run', 'mobility') for _, r in old)] + list(by_date)
        block, cycle_no = anchor, 0
        while block <= end:
            dates = [block + timedelta(days=i) for i in range(10) if start <= block+timedelta(days=i) <= end]
            factor = min(1.15, 1.03 ** cycle_no) * (.85 if cycle_no % 4 == 3 else 1)
            phase = 'Cykl indywidualny' if cycle_no % 4 != 3 else 'Cykl lżejszy'
            for event in events:
                distance = (date.fromisoformat(event['date']) - block).days
                if event['priority'] == 'A' and 0 <= distance <= 18:
                    factor = min(factor, .5 if distance <= 9 else .7)
                    phase = 'Taper przed startem A'
                elif event['priority'] == 'B' and 0 <= distance <= 9:
                    factor = min(factor, .8)
                    if 'Taper' not in phase:
                        phase = 'Cykl ze startem B'
            budget = sum(pattern[(d-anchor).days % 10]['distance_km'] for d in dates) * factor
            fixed = sum(number(r['planned_distance_km'] or 0) for d in dates for _, r in preserved.get(d, []))
            race_km = sum(by_date[d]['distance_km'] for d in dates if d in by_date and d not in preserved)
            open_dates = [d for d in dates if d not in preserved and d not in by_date and not self._recovering(d, events)]
            open_km = sum(pattern[(d-anchor).days % 10]['distance_km'] for d in open_dates)
            multiplier = min(factor, max(0, budget-fixed-race_km) / open_km) if open_km else 0
            total = fixed
            for day in dates:
                offset = (day-anchor).days % 10
                if day in preserved:
                    for row_no, row in preserved[day]:
                        entries.append({'row': row_no, 'action': 'keep', 'before': row, 'after': row, 'phase': 'Zachowana jednostka', 'cycle_day': offset+1})
                    continue
                unit = pattern[offset]
                reason = unit['reason']
                kind = unit['kind']
                km = math.floor(min(unit['distance_km'] * multiplier, limits['max_session_km'],
                    unit['distance_km'] * limits['max_session_minutes'] / unit['duration_min'] if unit['duration_min'] else 0) * 10) / 10
                minutes = round(unit['duration_min'] * km / unit['distance_km']) if unit['distance_km'] else 0
                if day in by_date:
                    event = by_date[day]
                    title, km, minutes = f'Zawody: {event["name"]}', event['distance_km'], ''
                    prescription = f'Start {event["priority"]}: {event["name"]}, {km:g} km. Cel zawodnika: {event["target_time"] or "ukończenie"}. {event["notes"]}'
                    reason = f'Kalendarz startów, priorytet {event["priority"]}'
                elif self._recovering(day, events) or kind == 'off' or minutes < 15:
                    title, km, minutes = 'Odpoczynek', 0, 0
                    prescription = 'Odpoczynek. Dzień bez treningu biegowego.'
                    if self._recovering(day, events):
                        reason = 'Regeneracja po starcie'
                else:
                    if kind in ('long', 'threshold') and (any(abs((day-h).days) < 3 for h in hard_dates) or
                            (kind == 'threshold' and ('Taper' in phase or any(0 <= (r-day).days < 7 for r in by_date)))):
                        kind = 'easy'
                        reason += ' Akcent zastąpiony spokojnym biegiem ze względu na odstęp od innych obciążeń.'
                    title = {'easy': 'Spokojny bieg', 'long': 'Długi spokojny bieg', 'threshold': 'Bieg progowy kontrolowany'}[kind]
                    if kind == 'threshold':
                        work = unit['repetitions'] * unit['work_min']
                        rest = (unit['repetitions']-1) * unit['recovery_min']
                        if minutes < 18 + work + rest:
                            title, kind = 'Spokojny bieg', 'easy'
                        else:
                            prescription = f'10 min spokojnej rozgrzewki; {unit["repetitions"]} x {unit["work_min"]} min threshold / kontrolowany próg, {unit["recovery_min"]} min truchtu między odcinkami; {minutes-10-work-rest} min schłodzenia. Łącznie około {minutes} min / {km:g} km.'
                    if kind != 'threshold':
                        prescription = f'{title} {km:g} km, około {minutes} min; równa, konwersacyjna intensywność.'
                    if kind in ('long', 'threshold'):
                        hard_dates.append(day)
                total += km
                old = rows_by_date.get(day, [])
                row_no, before = old[0] if old else (None, None)
                after = dict(before) if before else {h: '' for h in snapshot['headers']}
                note = f'PaceMind {today} | Zmiana: plan indywidualny, cykl 10-dniowy, dzień {offset+1}. Uzasadnienie: {reason}'
                description = ((before['description'] + MARKER) if before else '') + prescription + '\n' + note
                if len(description) > 50000:
                    raise ChatError(422, f'{day}: opis z historią przekracza limit komórki arkusza.')
                after.update(date=day.isoformat(), title=title, description=description, planned_distance_km=f'{km:g}',
                             planned_duration_min=str(minutes), priority=before['priority'] if before else ('key' if day in by_date else 'normal'))
                entries.append({'row': row_no, 'action': 'replace' if before else 'add', 'before': before, 'after': after, 'phase': reason, 'cycle_day': offset+1})
            cycles.append({'start': max(start, block).isoformat(), 'end': min(end, block+timedelta(days=9)).isoformat(),
                           'phase': phase, 'budget_km': round(budget, 1), 'planned_km': round(total, 1)})
            if total > budget + .5:
                warnings.append(f'Cykl od {max(start, block)}: starty lub zachowane jednostki przekraczają proponowaną objętość. Sprawdź podgląd.')
            block += timedelta(days=10)
            cycle_no += 1
        if preserved:
            warnings.append('Zachowane jednostki mogą ograniczać układ cyklu. Sprawdź odstępy i regenerację w podglądzie.')
        return {'entries': entries, 'cycles': cycles, 'weeks': [], 'warnings': warnings, 'blockers': blockers,
                'races': selected, 'can_accept': not blockers, 'cycle_days': 10}

    @staticmethod
    def _protected_description(description):
        final = description.rsplit('\nPaceMind ', 1)[-1]
        generated = 'Zmiana: plan pod kalendarz startów,' in final or 'Zmiana: plan indywidualny, cykl 10-dniowy,' in final
        return MARKER in description and not generated

    @staticmethod
    def _recovering(day, events):
        return any(0 < (day-date.fromisoformat(e['date'])).days <= recovery_days(e) for e in events)

    @staticmethod
    def _type(row):
        return PlannedWorkoutEngine().build(date.fromisoformat(row['date']), row['title'], row['description']).workout_type
