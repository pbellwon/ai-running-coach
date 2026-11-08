(() => {
    const el=name=>document.getElementById(`review-${name}`);
    const root=document.getElementById('plan-review');
    const labels={keep:'Utrzymaj dalszy plan',observe:'Obserwuj przed zmianą',reduce:'Propozycja zmniejszenia obciążenia',easy:'Propozycja spokojniejszych jednostek',clarify:'Potrzebne wyjaśnienie ograniczeń',insufficient_data:'Za mało danych do korekty'};
    const text=(tag,value)=>{const node=document.createElement(tag);node.textContent=value;return node;};
    let review=null,patch=null,busy=false,epoch=0,pendingReview=null,pendingPatch=null;
    const status=value=>{el('status').textContent=value;};
    async function request(path='',options){const previous=epoch;const value=await chatRequest(`/plan-reviews${path}`,options);if(previous!==epoch)throw new Error('Dostęp zamknięty.');return value;}
    function controls(){
        root.querySelectorAll('button,select').forEach(node=>{node.disabled=busy;});
        el('accept').hidden=!patch||!patch.can_accept||!['preview','writing'].includes(patch.status);
        el('reject').hidden=!patch||patch.status!=='preview';
        el('accept').textContent=patch?.status==='writing'?'Sprawdź wynik poprzedniego zapisu':'Akceptuję korektę i zapisuję do Google Sheets';
        el('run').textContent=busy?'Przetwarzanie…':'Oceń wykonanie i dalszy plan';
    }
    async function run(fn){if(busy)return;const previous=epoch;busy=true;controls();try{await fn();}catch(error){if(previous===epoch){status(error.message);el('status').tabIndex=-1;el('status').focus({preventScroll:true});el('status').scrollIntoView({block:'center'});}}finally{busy=false;controls();}}
    function showReview(value){
        review=value;patch=null;el('patch').hidden=true;el('result').hidden=false;
        el('title').textContent=labels[value.assessment.decision]||value.assessment.decision;
        el('period').textContent=`${value.period_start} – ${value.period_end}. Cel A: ${value.goal.name}, ${value.goal.date}.`;
        el('reason').textContent=value.assessment.reason;
        el('evidence').replaceChildren(...value.assessment.evidence.map(item=>text('li',item)));
        el('limitations').replaceChildren(...value.assessment.limitations.map(item=>text('li',item)));
        el('propose').hidden=!value.assessment.can_propose;
        el('days').replaceChildren();
        value.evidence.days.forEach(day=>{
            const item=document.createElement('details');item.append(text('summary',`${day.date} · ${{completed:'wykonano',off_completed:'odpoczynek',missed:'brak dopasowanego wykonania',partially_executed:'częściowo wykonano',pending:'dzień otwarty'}[day.status]||'przegląd dnia'}`));
            item.append(text('h5','Plan'));
            (day.planned_workouts||[]).forEach(unit=>item.append(text('p',`${unit.title||unit.workout_type||'Trening'} · ${unit.planned_distance_km??'—'} km · ${unit.planned_duration_min??'—'} min`)));
            item.append(text('h5','Wykonanie'));
            (day.executed_sessions||[]).forEach(unit=>{item.append(text('p',`${unit.workout_type||'Sesja'} · ${unit.total_distance_km??'—'} km · ${unit.total_duration_min??'—'} min. Ocena: ${{on_target:'zgodne z planem',too_hard:'większy bodziec niż plan',too_easy:'mniejszy bodziec niż plan',insufficient_evidence:'za mało danych'}[unit.execution_review?.status]||'brak oceny'}`));const feedback=unit.execution_review?.athlete_feedback;if(feedback)item.append(text('p',`Odczucia: RPE ${feedback.perceived_effort??'—'}. ${feedback.comment||feedback.execution_feeling||''}`));});
            el('days').append(item);
        });
        el('trends').textContent=`Trend istniejących ocen: ${value.evidence.goal_progress.fitness_trend}.\nRegeneracja: ${(value.evidence.current_recovery||value.evidence.recovery).fatigue_signal}.`;
        controls();el('title').focus({preventScroll:true});el('title').scrollIntoView({block:'start',behavior:'smooth'});
    }
    function showPatch(value){
        patch=value;el('patch').hidden=false;
        el('patch-summary').textContent=!value.can_accept?'Nie powstała korekta do zapisania. Sprawdź poniżej, które jednostki są chronione lub pozostają bez zmian.':`Korekta ${value.summary.replaced} jednostek w okresie ${value.start} – ${value.end}. Cel A i pozostałe części planu pozostają zachowane. Stan: ${{preview:'do akceptacji',applied:'zapisano',rejected:'odrzucono',writing:'do sprawdzenia'}[value.status]||value.status}.`;
        el('skipped').replaceChildren(...[...value.warnings,...value.blockers].map(item=>text('li',item)));
        el('changes').replaceChildren();
        for(const entry of value.entries){
            const details=document.createElement('details');details.open=true;details.append(text('summary',`${entry.after.date} · ${entry.after.title}`));
            const comparison=document.createElement('div');comparison.className='correction-comparison';
            for(const [label,row]of [['Przed',entry.before],['Po',entry.after]]){const column=document.createElement('div');column.append(text('h5',label),text('pre',`${row.title}\n${row.planned_distance_km} km · ${row.planned_duration_min} min\n${row.description}`));comparison.append(column);}
            details.append(comparison);el('changes').append(details);
        }
        controls();el('patch').scrollIntoView({block:'start',behavior:'smooth'});
    }
    el('run').addEventListener('click',()=>run(async()=>{
        review=patch=null;el('result').hidden=el('patch').hidden=true;controls();
        pendingReview=pendingReview||crypto.randomUUID();
        status('Porównuję wykonania z zaakceptowanym planem…');
        showReview(await request('',{method:'POST',body:JSON.stringify({id:pendingReview})}));pendingReview=null;
        status('Przegląd gotowy. Nic nie zostało zapisane do arkusza.');
    }));
    el('propose').addEventListener('submit',event=>{event.preventDefault();run(async()=>{
        const body={review_id:review.id,scope:el('scope').value},hash=JSON.stringify(body);
        if(!pendingPatch||pendingPatch.hash!==hash)pendingPatch={id:crypto.randomUUID(),hash};
        patch=null;el('patch').hidden=true;controls();
        showPatch(await request('/proposals',{method:'POST',body:JSON.stringify({id:pendingPatch.id,...body})}));pendingPatch=null;
        status('Sprawdź korektę przed i po. Zapis wymaga osobnej akceptacji.');
    });});
    for(const decision of ['accept','reject'])el(decision).addEventListener('click',()=>run(async()=>{
        if(decision==='accept'){patch.status='writing';controls();}
        showPatch(await request(`/proposals/${patch.id}/decision`,{method:'POST',body:JSON.stringify({decision})}));
        status(patch.status==='applied'?'Korekta zapisana i potwierdzona w Google Sheets.':'Korekta odrzucona.');
    }));
    el('history-load').addEventListener('click',()=>run(async()=>{
        const result=await request();el('history').replaceChildren();
        result.items.forEach(item=>{const button=document.createElement('button');button.type='button';button.textContent=`${item.period_start} – ${item.period_end} · ${labels[item.assessment.decision]}`;button.addEventListener('click',()=>{if(!busy)showReview(item);});el('history').append(button);});
    }));
    document.addEventListener('coach-access-closed',()=>{
        epoch++;review=patch=pendingReview=pendingPatch=null;el('result').hidden=el('patch').hidden=true;
        ['days','evidence','limitations','changes','skipped','history'].forEach(name=>el(name).replaceChildren());
        ['title','period','reason','trends','patch-summary'].forEach(name=>{el(name).textContent='';});status('');
    });controls();
})();
