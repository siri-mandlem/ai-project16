const API = window.LIBRARY_API_URL || '/api';
const userId = () => localStorage.getItem('library_user_id');
async function api(path, options = {}) {
    options.headers = {'Content-Type': 'application/json', ...(options.headers || {})};
    if (userId()) options.headers['X-User-Id'] = userId();
    const response = await fetch(`${API}${path}`, options); const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed'); return data;
}
function message(error) { alert(error.message || error); }
document.querySelector('#login-form')?.addEventListener('submit', async e => { e.preventDefault(); try { const data = await api('/auth/login', {method:'POST', body:JSON.stringify({email:e.target.email.value,password:e.target.password.value})}); localStorage.setItem('library_user_id', data.user_id); location.href='dashboard.html'; } catch (error) { message(error); } });
document.querySelector('#register-form')?.addEventListener('submit', async e => { e.preventDefault(); try { await api('/auth/register', {method:'POST', body:JSON.stringify({name:e.target.name.value,email:e.target.email.value,password:e.target.password.value})}); alert('Registered. Please log in.'); location.href='login.html'; } catch (error) { message(error); } });
document.querySelector('#search-form')?.addEventListener('submit', async e => { e.preventDefault(); try { const data = await api(`/books?q=${encodeURIComponent(e.target.q.value)}`); document.querySelector('#results').innerHTML = data.books.map(b=>`<article><h3>${b.title}</h3><p>${b.author} · ${b.available_copies}/${b.total_copies} available</p><button onclick="issueBook(${b.id})">Issue</button></article>`).join(''); } catch (error) { message(error); } });
async function issueBook(id) { try { await api('/issues',{method:'POST',body:JSON.stringify({book_id:id})}); alert('Book issued'); } catch(error) { message(error); } }
async function loadIssues() { try { const data=await api('/issues'); const target=document.querySelector('#issued-list'); if(target) target.innerHTML=data.issues.map(i=>`<article><h3>${i.book.title}</h3><p>Due: ${i.due_date} · Fine: ₹${i.fine_amount}</p>${i.status==='issued'?`<button onclick="returnBook(${i.id})">Return</button>`:'Returned'}</article>`).join(''); } catch(error) { message(error); } }
async function returnBook(id) { try { const data=await api(`/issues/${id}/return`,{method:'POST'}); alert(`Returned. Fine: ₹${data.fine_amount}`); loadIssues(); } catch(error) { message(error); } }
loadIssues();
