const API = window.LIBRARY_API_URL || '/api';
const userId = () => localStorage.getItem('library_user_id');
async function api(path, options = {}) {
    options.headers = {'Content-Type': 'application/json', ...(options.headers || {})};
    if (userId()) options.headers['X-User-Id'] = userId();
    const response = await fetch(`${API}${path}`, options); const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed'); return data;
}
function message(error) { alert(error.message || error); }
document.querySelector('#login-form')?.addEventListener('submit', async e => { e.preventDefault(); try { const data = await api('/auth/login', {method:'POST', body:JSON.stringify({email:e.target.email.value,password:e.target.password.value})}); localStorage.setItem('library_user_id', data.user_id); localStorage.setItem('library_user', JSON.stringify(data.user)); location.href='dashboard.html'; } catch (error) { message(error); } });
document.querySelector('#register-form')?.addEventListener('submit', async e => { e.preventDefault(); try { await api('/auth/register', {method:'POST', body:JSON.stringify({name:e.target.name.value,email:e.target.email.value,password:e.target.password.value})}); alert('Registered. Please log in.'); location.href='login.html'; } catch (error) { message(error); } });
document.querySelector('#search-form')?.addEventListener('submit', async e => { e.preventDefault(); try { const data = await api(`/books?q=${encodeURIComponent(e.target.q.value)}`); document.querySelector('#results').innerHTML = data.books.map(b=>`<article><h3>${b.title}</h3><p>${b.author} · ${b.available_copies}/${b.total_copies} available</p><button onclick="issueBook(${b.id})">Issue</button></article>`).join(''); } catch (error) { message(error); } });
async function issueBook(id) { try { await api('/issues',{method:'POST',body:JSON.stringify({book_id:id})}); alert('Book issued'); } catch(error) { message(error); } }
async function loadIssues() { try { const data=await api('/issues'); const target=document.querySelector('#issued-list'); if(target) target.innerHTML=data.issues.map(i=>`<article><h3>${i.book.title}</h3><p>Due: ${i.due_date} · Fine: ₹${i.fine_amount}</p>${i.status==='issued'?`<button onclick="returnBook(${i.id})">Return</button>`:'Returned'}</article>`).join(''); } catch(error) { message(error); } }
async function returnBook(id) { try { const data=await api(`/issues/${id}/return`,{method:'POST'}); alert(`Returned. Fine: ₹${data.fine_amount}`); loadIssues(); } catch(error) { message(error); } }
loadIssues();

function dashboardDate(date) { return new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {month: 'short', day: 'numeric'}); }
async function loadDashboard() {
    if (!userId()) { location.href = 'login.html'; return; }
    const user = JSON.parse(localStorage.getItem('library_user') || '{}');
    const nameTarget = document.querySelector('#user-name');
    if (nameTarget && user.name) nameTarget.textContent = user.name.split(' ')[0];
    try {
        const [bookData, issueData] = await Promise.all([api('/books'), api('/issues')]);
        const books = bookData.books; const issues = issueData.issues;
        const active = issues.filter(item => item.status === 'issued');
        const dueSoon = active.filter(item => { const days = Math.ceil((new Date(`${item.due_date}T00:00:00`) - new Date()) / 86400000); return days >= 0 && days <= 7; });
        document.querySelector('#total-books').textContent = books.length;
        document.querySelector('#available-copies').textContent = books.reduce((sum, book) => sum + book.available_copies, 0);
        document.querySelector('#active-loans').textContent = active.length; document.querySelector('#due-soon').textContent = dueSoon.length;
        document.querySelector('#recent-books').innerHTML = books.slice(0, 4).map(book => `<div class="book-row"><span class="book-cover">B</span><div><h3>${book.title}</h3><p>${book.author}</p></div><span class="availability">${book.available_copies} available</span></div>`).join('') || '<p class="empty-state">No books have been added yet.</p>';
        document.querySelector('#current-loans').innerHTML = active.slice(0, 4).map(item => `<div class="loan-row"><div><h3>${item.book.title}</h3><p>Due ${dashboardDate(item.due_date)}</p></div><span class="loan-status">${item.late_days ? 'Overdue' : 'Issued'}</span></div>`).join('') || '<p class="empty-state">You have no active loans. Browse the catalog to find a book.</p>';
    } catch (error) { document.querySelector('#recent-books').innerHTML = '<p class="empty-state">The catalog could not be loaded. Please refresh the page.</p>'; document.querySelector('#current-loans').innerHTML = '<p class="empty-state">Your loans could not be loaded. Please refresh the page.</p>'; message(error); }
}
document.querySelector('#logout-button')?.addEventListener('click', () => { localStorage.removeItem('library_user_id'); localStorage.removeItem('library_user'); location.href = 'login.html'; });
if (document.querySelector('.dashboard-page')) loadDashboard();
