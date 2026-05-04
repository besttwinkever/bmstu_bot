let currentDate;

function formatDateLabel(date) {
    return date.toLocaleDateString('ru-RU', {
        weekday: 'short',
        day: 'numeric',
        month: 'short'
    });
}

function getWeekDays(startMonday) {
    const days = [];
    const base = new Date(startMonday);
    base.setHours(0, 0, 0, 0);
    for (let i = 0; i < 7; i++) {
        const d = new Date(base);
        d.setDate(base.getDate() + i);
        days.push(d);
    }
    return days;
}

function isSameDay(d1, d2) {
    return d1.getFullYear() === d2.getFullYear()
        && d1.getMonth() === d2.getMonth()
        && d1.getDate() === d2.getDate();
}

function formatDateYYYYMMDD(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function loadWeekEvents() {
    currentDate.setHours(0, 0, 0, 0);
    const params = new URLSearchParams(window.location.search);
    const tgid = params.get('tgid');
    const uid = params.get('uid') || tgid;
    const platform = params.get('platform') || (tgid ? 'telegram' : '');
    const days = getWeekDays(currentDate);

    document.getElementById('current-week').textContent =
        `Неделя ${formatDateLabel(days[0])} - ${formatDateLabel(days[6])}`;

    const startDate = formatDateYYYYMMDD(days[0]);
    const endDate = formatDateYYYYMMDD(new Date(days[6].getTime() + 86400000));

    const weekContainer = document.getElementById('week-container');
    weekContainer.classList.remove('show');

    // 🔹 Ждём завершения скрытия и только потом перерисовываем
    setTimeout(() => {
        fetch(`/bot-app/api/calendar/events/?uid=${encodeURIComponent(uid || '')}&platform=${encodeURIComponent(platform)}&start=${startDate}&end=${endDate}`)
            .then(res => res.json())
            .then(data => {
                weekContainer.innerHTML = ''; // очистить старое
                days.forEach(day => {
                    const events = data.events.filter(e => {
                        const [d, m, yt] = e.date.split('.');
                        const [y, t] = yt.split(' ');
                        const date = new Date(`${y}-${m}-${d}T${t}`);
                        return isSameDay(date, day);
                    });

                    const dayCard = document.createElement('div');
                    dayCard.className = 'day-card';

                    const header = document.createElement('div');
                    header.className = 'day-header';
                    header.textContent = formatDateLabel(day);
                    dayCard.appendChild(header);

                    if (events.length) {
                        events.forEach(ev => {
                            const el = document.createElement('div');
                            el.className = 'event';
                            const [_, time] = ev.date.split(' ');
                            el.innerHTML = `<strong>${ev.title}</strong><p>${ev.description}</p><small>${time}</small>`;
                            el.dataset.title = ev.title;
                            el.dataset.description = ev.description;
                            el.dataset.datetime = ev.date;
                            el.dataset.groups = ev.groups || '—';
                            el.dataset.teacher = ev.teacher || '—';
                            el.addEventListener('click', () => {
                                document.getElementById('modal-title').textContent = el.dataset.title;
                                document.getElementById('modal-description').textContent = el.dataset.description;
                                document.getElementById('modal-datetime').textContent = el.dataset.datetime;
                                document.getElementById('modal-groups').textContent = el.dataset.groups;
                                document.getElementById('modal-teacher').textContent = el.dataset.teacher;
                                document.body.classList.add('modal-open');
                                const modal = document.getElementById('event-modal');
                                const backdrop = document.getElementById('modal-backdrop');
                                modal.classList.remove('hidden');
                                backdrop.classList.remove('hidden');
                                
                                requestAnimationFrame(() => {
                                    modal.classList.add('show');
                                    backdrop.classList.add('show');
                                });
                            });
                            dayCard.appendChild(el);
                        });
                    } else {
                        const no = document.createElement('div');
                        no.className = 'no-events';
                        no.textContent = 'Нет событий';
                        dayCard.appendChild(no);
                    }

                    weekContainer.appendChild(dayCard);
                });

                // 🔹 Добавляем анимацию появления
                weekContainer.classList.add('show');
            });
    }, 150); // немного подождать, чтобы спрятать старое
}

document.addEventListener('DOMContentLoaded', () => {
    const now = new Date();
    const day = now.getDay(); // 0 - воскресенье, 1 - понедельник ...
    const offset = day === 0 ? -6 : 1 - day;
    now.setDate(now.getDate() + offset);
    now.setHours(0, 0, 0, 0);
    currentDate = now;
    
    loadWeekEvents();
    // document.getElementById("debug-log").textContent = `start=${currentDate}, end=${currentDate}`;
    document.getElementById('prev-week').addEventListener('click', () => {
        currentDate.setDate(currentDate.getDate() - 7);
        loadWeekEvents();
    });

    document.getElementById('next-week').addEventListener('click', () => {
        currentDate.setDate(currentDate.getDate() + 7);
        loadWeekEvents();
    });

    document.getElementById('download-ics').addEventListener('click', () => {
        const params = new URLSearchParams(window.location.search);
        const tgid = params.get('tgid');
        const uid = params.get('uid') || tgid;
        const platform = params.get('platform') || (tgid ? 'telegram' : '');
        const days = getWeekDays(currentDate);
        const start = formatDateYYYYMMDD(days[0]);
        const end = formatDateYYYYMMDD(new Date(days[6].getTime() + 86400000)); // +1 день
        document.getElementById("debug-log").textContent = `start=${start}, end=${end}`;
        const url = `/api/calendar/export_ics/?uid=${encodeURIComponent(uid || '')}&platform=${encodeURIComponent(platform)}&start=${start}&end=${end}`;
        window.open(url, '_blank');
    });

    document.getElementById('modal-close').addEventListener('click', () => {
    const modal = document.getElementById('event-modal');
    const backdrop = document.getElementById('modal-backdrop');
    modal.classList.remove('show');
    backdrop.classList.remove('show');
    setTimeout(() => {
        modal.classList.add('hidden');
        backdrop.classList.add('hidden');
        document.body.classList.remove('modal-open');
    }, 300); // как у transition в .modal
    });
});
