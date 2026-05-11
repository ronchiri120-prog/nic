/**
 * CRM Page - Customer Interactions
 */
Auth.require();
// API availability guard
if (typeof API === 'undefined') {
  document.body.className = 'ql-fatal-error';
  document.body.innerHTML = '<div class="ql-fatal-box"><div class="ql-fatal-icon">⚠️</div><div>api.js failed to load.<br>Refresh or restart the backend.</div></div>';
  throw new Error('api.js not loaded');
}
Auth.requireRole(['SUPER_ADMIN','BRANCH_MANAGER','RM','OPERATIONS','COLLECTIONS','COLLECTIONS_MGR','LOAN_OFFICER','IDC','BDO','VERIFICATION_TEAM']);

let mediaRecorder = null;
let audioChunks = [];
let currentCustomerId = null;

document.addEventListener('DOMContentLoaded', () => {
  loadSidebar('crm');
  loadCRMInteractions();
  loadCustomers();
});

async function loadCRMInteractions(url) {
  const tbody = document.getElementById('crmTbody');
  tbody.innerHTML = '<tr><td colspan="8" class="text-center">Loading...</td></tr>';

  const params = {
    method: document.getElementById('methodFilter')?.value || '',
    outcome: document.getElementById('outcomeFilter')?.value || '',
    search: document.getElementById('searchInput')?.value || '',
  };

  try {
    const data = url
      ? await fetch(url, { headers: { Authorization: `Bearer ${Auth.getToken()}` } }).then(r => r.json())
      : await API.crmInteractions(params);
    const interactions = data?.results || [];
    const count = data?.count ?? interactions.length;

    document.getElementById('stat-total').textContent = count.toLocaleString();

    tbody.innerHTML = interactions.length
      ? interactions.map(crm => `
        <tr>
          <td>
            <b>${crm.customer_name || '—'}</b><br>
            <span class="text-sm text-dim">${crm.customer_phone || '—'}</span>
          </td>
          <td>${crm.customer_branch || '—'}</td>
          <td><span class="chip">${crm.conversation_method || '—'}</span></td>
          <td>${crm.conversation_purpose || '—'}</td>
          <td>
            <span class="badge ${crm.outcome === 'PTP' ? 'badge-success' : crm.outcome === 'DEFAULT' ? 'badge-danger' : 'badge-default'}">
              ${crm.outcome || '—'}
            </span>
          </td>
          <td>
            ${crm.ptp_amount ? `${Fmt.currency(crm.ptp_amount)}` : '—'}
            ${crm.ptp_date ? `<br><span class="text-xs text-dim">${Fmt.date(crm.ptp_date)}</span>` : ''}
          </td>
          <td>${crm.next_step || '—'}</td>
          <td>${crm.recorded_by_name || '—'}</td>
          <td>${Fmt.datetime(crm.created_at)}</td>
          <td>
            <button class="btn btn-ghost btn-sm" onclick="viewCRM(${crm.id})">👁️ View</button>
            <button class="btn btn-ghost btn-sm text-red" onclick="deleteCRM(${crm.id})">🗑️</button>
          </td>
        </tr>
      `).join('')
      : `<tr><td colspan="10" class="text-center">No interactions found</td></tr>`;

    renderPagination('crmPagination', data, 'loadCRMInteractions');
  } catch {
    tbody.innerHTML = `<tr><td colspan="10" class="td-error">Failed to load interactions.</td></tr>`;
  }
}

async function loadCustomers() {
  try {
    const data = await API.customers({ page_size: 1000 });
    const customers = data?.results || [];
    const select = document.getElementById('crmCustomer');
    select.innerHTML = '<option value="">Select Customer</option>' +
      customers.map(c => `<option value="${c.id}">${c.full_name} (${c.phone})</option>`).join('');
  } catch (err) {
    console.error('Failed to load customers:', err);
  }
}

async function onCustomerChange() {
  const customerId = document.getElementById('crmCustomer').value;
  currentCustomerId = customerId;
  
  if (!customerId) {
    document.getElementById('crmCustomerName').value = '';
    document.getElementById('crmCustomerPhone').value = '';
    document.getElementById('crmLoan').innerHTML = '<option value="">Select Loan</option>';
    return;
  }

  try {
    const customer = await API.customer(customerId);
    document.getElementById('crmCustomerName').value = customer.full_name || '';
    document.getElementById('crmCustomerPhone').value = customer.phone || '';

    // Load customer's loans
    const loans = await API.customerLoans(customerId);
    const loanSelect = document.getElementById('crmLoan');
    loanSelect.innerHTML = '<option value="">Select Loan</option>' +
      loans.filter(l => l.status === 'ACTIVE' || l.status === 'DEFAULT')
        .map(l => `<option value="${l.id}">${l.loan_id} - ${Fmt.currency(l.principal)}</option>`)
        .join('');
  } catch (err) {
    console.error('Failed to load customer:', err);
  }
}

function onOutcomeChange() {
  const outcome = document.getElementById('crmOutcome').value;
  const ptpSection = document.getElementById('ptpSection');
  ptpSection.style.display = outcome === 'PTP' ? 'block' : 'none';
}

function openCRMModal() {
  document.getElementById('crmForm').reset();
  document.getElementById('ptpSection').style.display = 'none';
  clearRecording();
  Modal.open('modal-crm');
}

async function saveCRM() {
  const data = {
    customer: document.getElementById('crmCustomer').value,
    loan: document.getElementById('crmLoan').value || null,
    conversation_method: document.getElementById('crmMethod').value,
    conversation_purpose: document.getElementById('crmPurpose').value,
    reason_for_default: document.getElementById('crmReason').value || null,
    outcome: document.getElementById('crmOutcome').value,
    outcome_details: document.getElementById('crmOutcomeDetails').value,
    recording_transcript: document.getElementById('crmTranscript').value,
    next_interaction_date: document.getElementById('crmNextDate').value || null,
    next_step: document.getElementById('crmNextStep').value || null,
    ptp_amount: document.getElementById('crmPTPAmount').value || null,
    ptp_date: document.getElementById('crmPTPDate').value || null,
  };

  if (!data.customer || !data.conversation_method || !data.conversation_purpose || !data.outcome) {
    Toast.error('Please fill all required fields');
    return;
  }

  setLoading('btnSaveCRM', true);
  try {
    const result = await API.createCRM(data);
    if (result) {
      Toast.success('CRM interaction saved successfully');
      Modal.close('modal-crm');
      loadCRMInteractions();
    }
  } catch (err) {
    Toast.error(err?.data?.detail || 'Failed to save interaction');
  } finally {
    setLoading('btnSaveCRM', false);
  }
}

async function viewCRM(id) {
  try {
    const crm = await API.crmInteraction(id);
    // TODO: Open detail modal with CRM data
    Toast.info('View functionality coming soon');
  } catch (err) {
    Toast.error('Failed to load interaction');
  }
}

async function deleteCRM(id) {
  if (!await QL.confirm('Delete this interaction?', { title: 'Delete CRM', okLabel: 'Delete', okClass: 'btn-danger' })) return;
  try {
    await API.deleteCRM(id);
    Toast.success('Interaction deleted');
    loadCRMInteractions();
  } catch (err) {
    Toast.error('Failed to delete interaction');
  }
}

async function loadPTPToday() {
  try {
    const data = await API.crmPTPToday();
    const tbody = document.getElementById('crmTbody');
    document.getElementById('stat-ptp').textContent = data.length.toLocaleString();
    
    tbody.innerHTML = data.length
      ? data.map(crm => `
        <tr>
          <td><b>${crm.customer_name || '—'}</b><br><span class="text-sm text-dim">${crm.customer_phone || '—'}</span></td>
          <td><span class="chip">${crm.conversation_method || '—'}</span></td>
          <td>${crm.conversation_purpose || '—'}</td>
          <td><span class="badge badge-success">${crm.outcome || '—'}</span></td>
          <td>${crm.ptp_amount ? `${Fmt.currency(crm.ptp_amount)}<br><span class="text-xs text-dim">${Fmt.date(crm.ptp_date)}</span>` : '—'}</td>
          <td>${crm.next_step || '—'}</td>
          <td>${Fmt.datetime(crm.created_at)}</td>
          <td>
            <button class="btn btn-ghost btn-sm" onclick="viewCRM(${crm.id})">👁️ View</button>
          </td>
        </tr>
      `).join('')
      : `<tr><td colspan="8" class="text-center">No PTP for today</td></tr>`;
  } catch (err) {
    Toast.error('Failed to load PTP data');
  }
}

async function loadFollowUps() {
  try {
    const data = await API.crmFollowUps();
    const tbody = document.getElementById('crmTbody');
    document.getElementById('stat-followups').textContent = data.length.toLocaleString();
    
    tbody.innerHTML = data.length
      ? data.map(crm => `
        <tr>
          <td><b>${crm.customer_name || '—'}</b><br><span class="text-sm text-dim">${crm.customer_phone || '—'}</span></td>
          <td><span class="chip">${crm.conversation_method || '—'}</span></td>
          <td>${crm.conversation_purpose || '—'}</td>
          <td><span class="badge">${crm.outcome || '—'}</span></td>
          <td>—</td>
          <td>${crm.next_step || '—'}</td>
          <td><span class="text-brand">${Fmt.date(crm.next_interaction_date)}</span></td>
          <td>
            <button class="btn btn-ghost btn-sm" onclick="viewCRM(${crm.id})">👁️ View</button>
          </td>
        </tr>
      `).join('')
      : `<tr><td colspan="8" class="text-center">No pending follow-ups</td></tr>`;
  } catch (err) {
    Toast.error('Failed to load follow-ups');
  }
}

const onSearch = debounce(() => loadCRMInteractions(), 350);

// ─── Voice Recognition ─────────────────────────────────────────
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      
      // For now, just show the transcript placeholder
      // In production, you'd upload the audio file to the server
      document.getElementById('recordingStatus').textContent = 'Processing audio...';
      
      // Simulate transcript (replace with actual speech-to-text API)
      setTimeout(() => {
        document.getElementById('crmTranscript').value = '[Transcript will be generated from audio recording]';
        document.getElementById('recordingStatus').textContent = 'Recording saved';
      }, 1000);
    };

    mediaRecorder.start();
    document.getElementById('btnStartRecording').disabled = true;
    document.getElementById('btnStopRecording').disabled = false;
    document.getElementById('recordingStatus').textContent = '🔴 Recording...';
  } catch (err) {
    Toast.error('Could not access microphone: ' + err.message);
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
    document.getElementById('btnStartRecording').disabled = false;
    document.getElementById('btnStopRecording').disabled = true;
  }
}

function clearRecording() {
  audioChunks = [];
  document.getElementById('crmTranscript').value = '';
  document.getElementById('recordingStatus').textContent = '';
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
    document.getElementById('btnStartRecording').disabled = false;
    document.getElementById('btnStopRecording').disabled = true;
  }
}
