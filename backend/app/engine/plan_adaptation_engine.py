"""Conservative, evidence-linked decisions; no diagnosis or automatic load increase."""
from collections import Counter


class PlanAdaptationEngine:
    def evaluate(self,evidence,profile):
        days=evidence['days']
        sessions=[s for d in days for s in d['executed_sessions']]
        reviews=[s.get('execution_review',{}) for s in sessions]
        reliable=[r for r in reviews if (r.get('confidence') or 0)>=.5]
        counts=Counter(r.get('status') for r in reliable)
        recovery=evidence.get('current_recovery',evidence['recovery'])
        fatigue=recovery.get('fatigue_signal','insufficient_data')
        available=recovery.get('available_days',0)
        limitations=['Ocena wykonania opisuje zgodność bodźca z planem, nie jest sama w sobie pomiarem wzrostu formy.',
                      'Sygnały zmęczenia nie są rozpoznaniem przetrenowania. Brak zapisu może oznaczać brak synchronizacji.']
        feedback_count=sum(bool(r.get('athlete_feedback')) for r in reviews)
        if not feedback_count: limitations.append('Brak odczuć do ocenionych sesji; brak zgłoszenia dolegliwości nie potwierdza pełnej regeneracji.')
        facts=[f'Sesje z dołączonym feedbackiem: {feedback_count}.',f'Zapisane sesje: {len(sessions)}; wiarygodne oceny: {len(reliable)}; too_hard: {counts["too_hard"]}.',
               f'Dni z regeneracją: {available}; sygnał: {fatigue}.']
        injuries=[m for m in profile.get('memory',[]) if m.get('category')=='injury' and m.get('status') in ('current','unreviewed')]
        if injuries:
            return self._result('clarify','W profilu jest aktualne zgłoszenie kontuzji. Doprecyzuj ograniczenia z trenerem przed zmianą obciążeń.',facts,limitations,counts)
        if not sessions or len(reliable)<2 or available<2 or fatigue=='insufficient_data':
            return self._result('insufficient_data','Za mało wiarygodnych danych do automatycznej propozycji korekty. Uzupełnij wykonania, odczucia i regenerację.',facts,limitations,counts)
        if counts['too_hard']>=2 and fatigue in ('watch','high','accumulating'):
            return self._result('reduce','Powtarzająca się trudność sesji i pogorszenie regeneracji wspierają zmniejszenie obciążenia dalszego planu.',facts,limitations,counts)
        if fatigue in ('high','accumulating'):
            return self._result('easy','Sygnały regeneracji wspierają zastąpienie najbliższych akcentów spokojnym biegiem i ponowny przegląd.',facts,limitations,counts)
        if counts['too_hard'] or evidence['goal_progress'].get('fitness_trend')=='declining':
            return self._result('observe','Sygnały są niejednoznaczne. Zachowaj plan, zbierz odczucia i obserwuj trend; nie zwiększaj obciążeń na podstawie jednej oceny.',facts,limitations,counts)
        return self._result('keep','Dostępne oceny wspierają utrzymanie dalszej struktury planu. Nie stanowi to gwarancji gotowości do startu A.',facts,limitations,counts)

    @staticmethod
    def _result(decision,reason,evidence,limitations,counts):
        return {'decision':decision,'reason':reason,'evidence':evidence,'limitations':limitations,
                'execution_counts':dict(counts),'can_propose':decision in ('reduce','easy')}
