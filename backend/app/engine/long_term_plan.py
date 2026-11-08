"""A complete preparation arc anchored to the confirmed A race, in ten-day cycles."""
from copy import deepcopy
from datetime import date, timedelta
import math

LABELS = {'foundation':'Baza i tolerancja obciążeń', 'development':'Rozwój obciążenia',
          'specific':'Przygotowanie specyficzne', 'taper':'Taper przed startem A', 'recovery':'Regeneracja po starcie A'}
ROLES = {'foundation':'Zbudować powtarzalność i tolerancję bez zwiększania intensywności.',
         'development':'Stopniowo rozwijać objętość i kontrolowaną pracę progową.',
         'specific':'Połączyć wytrzymałość i akcenty dobrane do dystansu głównego startu.',
         'taper':'Zmniejszyć zmęczenie przed głównym startem, zachowując rytm treningu.',
         'recovery':'Odbudować regenerację po głównym starcie; bez dokładania akcentów.'}


class LongTermPlan:
    def __init__(self, start, end, strategy, events, limits, goal=None, preparation_start=None):
        self.start, self.end, self.strategy, self.limits = start, end, strategy, limits
        self.preparation_start = preparation_start or start
        self.goal = goal or next(e for e in events if e['priority']=='A' and start.isoformat() <= e['date'] <= end.isoformat())
        self.race_day = date.fromisoformat(self.goal['date'])
        self.anchor = start-timedelta(days=strategy['start_offset'])
        self.taper_days = 21 if self.goal['distance_km'] > 21.1 else 14 if self.goal['distance_km'] > 10 else 10
        self.taper_start = max(self.preparation_start, self.race_day-timedelta(days=self.taper_days))
        available = (self.taper_start-self.preparation_start).days
        self.base_end = self.preparation_start+timedelta(days=available//3)
        self.specific_start = self.preparation_start+timedelta(days=available*2//3)
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
        elapsed = max(0,(max(self.preparation_start,block)-self.preparation_start).days)
        progress = min(1, elapsed/max(1,(self.taper_start-self.preparation_start).days))
        quality_progress = min(1,max(0,(max(self.start,block)-self.start).days)/max(1,(self.taper_start-self.start).days))
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
                'progress':progress,
                'quality_progress':quality_progress,
                'checkpoint':'Po wykonaniu oceń odczucia, regenerację i realizację bodźców przed zmianą dalszego planu.'}

    def pattern(self, cycle):
        pattern = {d['offset']:deepcopy(d) for d in self.strategy['days']}
        phase = cycle['phase_key']
        for unit in pattern.values():
            if unit['kind']=='threshold':
                observed=self.limits.get('observed_threshold_work_min',0)
                if phase in ('taper','recovery') or cycle['deload'] or (phase=='foundation' and not observed):
                    unit.update(kind='easy',repetitions=0,work_min=0,recovery_min=0)
                else:
                    # Keep the coach's interval format. A short return-to-running seed
                    # must not become a permanent ceiling for an experienced athlete.
                    seed=unit['repetitions']*unit['work_min']
                    reference=max(seed,observed)
                    target=reference*{'foundation':.8,'development':1,'specific':1.2}[phase]
                    ceiling=seed+max(0,reference*1.2-seed)*cycle.get('quality_progress',cycle.get('progress',0))
                    if not observed: ceiling=min(ceiling,seed*cycle['envelope'])
                    work=min(40,math.floor(min(target,ceiling)/unit['repetitions']))
                    if work>=2:
                        unit['work_min']=work
                        unit['reason']+=f' Próg: {unit["repetitions"]} x {work} min pracy; dawka z propozycji trenera i rozpoznanej historii, nie z samego czasu docelowego.'
                    else:
                        unit.update(kind='easy',repetitions=0,work_min=0,recovery_min=0)
            if phase=='recovery' and unit['kind']=='long': unit['kind']='easy'
            if unit['kind']=='strength' and phase in ('taper','recovery'):
                unit.update(kind='off',distance_km=0,duration_min=0,strength_exercises=[])
                unit['reason']+=' Siła pominięta w taperze lub regeneracji po starcie A.'
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
        day=self.preparation_start
        while day<=self.end:
            key=self.phase(day)
            if phases and phases[-1]['key']==key: phases[-1]['end']=day.isoformat()
            else: phases.append({'key':key,'name':LABELS[key],'start':day.isoformat(),'end':day.isoformat(),'role':ROLES[key]})
            day+=timedelta(days=1)
        warnings=[]
        if not self.limits.get('observed_threshold_work_min'):
            warnings.append('Brak rozpoznanej dawki pracy progowej z odcinków wykonania. Progresja pozostaje ograniczona propozycją trenera; brak danych o odcinkach nie oznacza braku doświadczenia.')
        if (self.race_day-self.preparation_start).days < self.taper_days+30:
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
        return {'goal':self.goal,'cycle_days':10,'start':self.preparation_start.isoformat(),'end':self.end.isoformat(),
                'phases':phases,'warnings':warnings,
                'assumptions':['Najbliższy cykl opiera się na obserwowanym obciążeniu; dalsza progresja jest propozycją do weryfikacji.',
                    'Praca progowa zachowuje format dobrany przez trenera i jest ograniczona historią odcinków oraz czasem jednostki; nie ma stałego limitu 2x8 min.',
                    'Siła ma własne jednostki; kolizje ze startami i taper/regeneracja mogą uzasadniać jej pominięcie.',
                    'Starty B/C wspierają przygotowania do wskazanego A; nie zmieniają celu głównego.',
                    'Dalszy plan podlega przeglądowi wykonań i regeneracji; każda zmiana wymaga podglądu i akceptacji.']}
