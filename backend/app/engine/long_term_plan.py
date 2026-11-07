"""A complete preparation arc anchored to the confirmed A race, in ten-day cycles."""
from copy import deepcopy
from datetime import date, timedelta

LABELS = {'foundation':'Baza i tolerancja obciążeń', 'development':'Rozwój obciążenia',
          'specific':'Przygotowanie specyficzne', 'taper':'Taper przed startem A', 'recovery':'Regeneracja po starcie A'}
ROLES = {'foundation':'Zbudować powtarzalność i tolerancję bez zwiększania intensywności.',
         'development':'Stopniowo rozwijać objętość i kontrolowaną pracę progową.',
         'specific':'Połączyć wytrzymałość i akcenty dobrane do dystansu głównego startu.',
         'taper':'Zmniejszyć zmęczenie przed głównym startem, zachowując rytm treningu.',
         'recovery':'Odbudować regenerację po głównym starcie; bez dokładania akcentów.'}


class LongTermPlan:
    def __init__(self, start, end, strategy, events, limits, goal=None):
        self.start, self.end, self.strategy, self.limits = start, end, strategy, limits
        self.goal = goal or next(e for e in events if e['priority']=='A' and start.isoformat() <= e['date'] <= end.isoformat())
        self.race_day = date.fromisoformat(self.goal['date'])
        self.anchor = start-timedelta(days=strategy['start_offset'])
        self.taper_days = 21 if self.goal['distance_km'] > 21.1 else 14 if self.goal['distance_km'] > 10 else 10
        self.taper_start = max(start, self.race_day-timedelta(days=self.taper_days))
        available = (self.taper_start-start).days
        self.base_end = start+timedelta(days=available//3)
        self.specific_start = start+timedelta(days=available*2//3)
        self.last_peak = None
        self.events = [e for e in events if start.isoformat() <= e['date'] <= end.isoformat()]

    def phase(self, day):
        if day > self.race_day: return 'recovery'
        if day >= self.taper_start: return 'taper'
        if day < self.base_end: return 'foundation'
        if day < self.specific_start: return 'development'
        return 'specific'

    def cycle(self, block, number):
        dates = [block+timedelta(days=i) for i in range(10) if self.start <= block+timedelta(days=i) <= self.end]
        # A mixed cycle adopts the later preparation stage; daily taper/recovery still override it.
        phase = self.phase(dates[0])
        elapsed = max(0,(max(self.start,block)-self.start).days)
        progress = min(1, elapsed/max(1,(self.taper_start-self.start).days))
        envelope = min(1.4, 1.04**number)
        target = {'foundation':.9+progress*.2, 'development':1+progress*.25,
                  'specific':1+progress*.4, 'taper':.65, 'recovery':.5}[phase]
        factor = min(envelope,target)
        if phase in ('foundation','development','specific'):
            if self.last_peak is not None: factor = min(factor,self.last_peak*1.04)
        deload = number%3 == 2 and phase not in ('taper','recovery')
        if deload: factor *= .8
        elif phase in ('foundation','development','specific'): self.last_peak = factor
        role = ROLES[phase]
        if deload: role += ' Cykl odciążający po dwóch cyklach pracy.'
        return {'phase_key':phase, 'phase':LABELS[phase]+(' · odciążenie' if deload else ''),
                'role':role,'factor':factor,'envelope':envelope,'deload':deload,
                'checkpoint':'Po wykonaniu oceń odczucia, regenerację i realizację bodźców przed zmianą dalszego planu.'}

    def pattern(self, cycle):
        pattern = {d['offset']:deepcopy(d) for d in self.strategy['days']}
        phase = cycle['phase_key']
        for unit in pattern.values():
            if unit['kind']=='threshold':
                if phase in ('foundation','taper','recovery') or cycle['deload']:
                    unit.update(kind='easy',repetitions=0,work_min=0,recovery_min=0)
                else:
                    # Doses differ by preparation stage and main distance, never by predicted race pace.
                    reps = 2 if self.goal['distance_km'] > 10 else (3 if phase=='development' else 4)
                    work = 4 if phase=='development' else (8 if reps==2 else 4)
                    rest = 2
                    dose_cap = unit['repetitions']*unit['work_min']*cycle['envelope']
                    while reps*work > dose_cap and work>2: work -= 1
                    while reps*work > dose_cap and reps>2: reps -= 1
                    while work>2 and 18+reps*work+(reps-1)*rest > unit['duration_min']:
                        work -= 1
                    if 18+reps*work+(reps-1)*rest <= unit['duration_min']:
                        unit.update(repetitions=reps,work_min=work,recovery_min=rest)
                    else:
                        unit.update(kind='easy',repetitions=0,work_min=0,recovery_min=0)
            if phase=='recovery' and unit['kind']=='long': unit['kind']='easy'
            unit['reason'] += f' {cycle["role"]} Cel: {self.goal["name"]} ({self.goal["date"]}).'
        return pattern

    def daily_factor(self, day):
        if day > self.race_day: return .5
        delta = (self.race_day-day).days
        if 0 < delta <= self.taper_days:
            return .5 if delta <= 5 else .65 if delta <= 10 else .8
        # B is a control start; C consumes a hard day without a separate peak.
        if any(e['priority']=='B' and 0 < (date.fromisoformat(e['date'])-day).days <= 3 for e in self.events):
            return .75
        return 1.4

    def manifest(self):
        phases=[]
        day=self.start
        while day<=self.end:
            key=self.phase(day)
            if phases and phases[-1]['key']==key: phases[-1]['end']=day.isoformat()
            else: phases.append({'key':key,'name':LABELS[key],'start':day.isoformat(),'end':day.isoformat(),'role':ROLES[key]})
            day+=timedelta(days=1)
        warnings=[]
        if (self.race_day-self.start).days < self.taper_days+30:
            warnings.append('Krótki okres do startu A ogranicza rozwój. Plan nie zastępuje brakujących przygotowań i nie gwarantuje wyniku.')
        long_distance = max((d['distance_km'] for d in self.strategy['days'] if d['kind']=='long'),default=0)
        if self.goal['distance_km'] > 10 and long_distance*1.4 < self.goal['distance_km']*.5:
            warnings.append('Obserwowane obciążenie ogranicza długość wybiegań względem dystansu A. Plan nie potwierdza gotowości do tego dystansu; cel wymaga oceny.')
        for other in self.events:
            if other['priority']=='A' and other != self.goal:
                warnings.append(f'{other["name"]}: dodatkowy start A nie zastępuje potwierdzonego celu głównego; pełny taper dotyczy wybranego celu.')
        for a,b in zip(self.events,self.events[1:]):
            if (date.fromisoformat(b['date'])-date.fromisoformat(a['date'])).days < 7:
                warnings.append(f'Bliskie starty: {a["name"]} i {b["name"]}. Wymagają ostrożnej oceny regeneracji.')
        return {'goal':self.goal,'cycle_days':10,'start':self.start.isoformat(),'end':self.end.isoformat(),
                'phases':phases,'warnings':warnings,
                'assumptions':['Najbliższy cykl opiera się na obserwowanym obciążeniu; dalsza progresja jest propozycją do weryfikacji.',
                    'Starty B/C wspierają przygotowania do wskazanego A; nie zmieniają celu głównego.',
                    'Przegląd cyklu nie uruchamia samoczynnie nowego planu. Adaptacja po wykonaniu należy do kolejnego sprintu.']}
