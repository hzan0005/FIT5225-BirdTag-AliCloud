<template>
  <div id="app-container">
    <div class="background-gradient"></div>
    <main id="app">
      <header class="app-header">
        <h1>🐦 BirdTag</h1>
        <p>A Modern Serverless Image Platform</p>
      </header>

      <div v-if="notification.message" :class="['notification', notification.type, {show: notification.show}]">
        {{ notification.message }}
      </div>

      <div class="card auth-card">
        <h2><i class="icon">👤</i>Authentication</h2>
        <div class="form-group">
          <input v-model="email" type="email" placeholder="Email Address" />
          <input v-model="password" type="password" placeholder="Password" />
        </div>
        <div class="button-group">
          <button @click="register" :disabled="loading">Register</button>
          <button @click="login" :disabled="loading" class="primary">Login</button>
        </div>
        <div v-if="token" class="token-display">
          Logged in successfully!
        </div>
      </div>

      <div class="card-grid">
        <div class="card">
          <h2><i class="icon">🔍</i>File Query</h2>
          <div class="form-group vertical">
            <label>Search by Species Name</label>
            <input v-model="speciesToSearch" @keyup.enter="searchBySpecies" placeholder="e.g., Kingfisher" />
            <button @click="searchBySpecies" :disabled="!token || loading" class="full-width">Search</button>
          </div>
          <hr/>
          <div class="form-group vertical">
            <label>Search by Tags & Counts (JSON)</label>
            <input v-model="countQuery" @keyup.enter="queryByCount" placeholder='e.g., {"Kingfisher": 1}' />
            <button @click="queryByCount" :disabled="!token || loading" class="full-width">Search by Count</button>
          </div>
        </div>

        <div class="card">
          <h2><i class="icon">⚙️</i>File Management</h2>
          <div class="form-group vertical">
            <label>File URL to Manage</label>
            <input v-model="urlToManage" placeholder="Enter original file URL" />
            <label>Tag to Add/Remove</label>
            <input v-model="tagsToManage" placeholder="e.g., rare,1" />
            <div class="button-group">
              <button @click="manageTags(1)" :disabled="!token || loading">Add Tag</button>
              <button @click="manageTags(0)" :disabled="!token || loading" class="button-danger">Remove Tag</button>
            </div>
          </div>
          <hr/>
          <div class="form-group vertical">
            <label>Permanently Delete File</label>
            <input v-model="urlToDelete" placeholder="Enter original file URL to delete" />
            <button @click="deleteFile" :disabled="!token || loading" class="button-danger full-width">Delete File</button>
          </div>
        </div>

        <div class="card upload-card">
          <h2><i class="icon">☁️</i>Upload & Search</h2>
          <div class="form-group vertical">
            <label>Upload an image to find similar files</label>
            <input type="file" @change="handleFileUpload" accept="image/*" class="file-input"/>
            <button @click="searchByFile" :disabled="!token || loading" class="full-width">Upload & Search</button>
          </div>
        </div>
      </div>

      <div class="card">
        <h2><i class="icon">📋</i>Action Result</h2>
        <div v-if="loading" class="loading-spinner"></div>
        <div v-else class="result-text-area" :class="{ 'error-text': hasError }">
            {{ userFriendlyResult }}
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const API_GATEWAY_DOMAIN = "https://9b618e52ff3d4250a85f65db6a017f03-cn-hangzhou.alicloudapi.com";

const email = ref('testuser-demo@example.com');
const password = ref('StrongPassword123');
const token = ref(null);
const speciesToSearch = ref('Kingfisher');
const countQuery = ref('{"Kingfisher": 1}');
const fileToUpload = ref(null);
const urlToManage = ref('https://birdtag-media-5225.oss-cn-hangzhou.aliyuncs.com/uploads/kingfisher_2.jpg');
const tagsToManage = ref('rare,1');
const urlToDelete = ref('');
const loading = ref(false);
const hasError = ref(false);
const notification = ref({ message: '', type: 'success', show: false });
const userFriendlyResult = ref('Welcome! Your operation results will be shown here.');

function showNotification(message, type = 'success', duration = 3000) {
  notification.value = { message, type, show: true };
  setTimeout(() => {
    notification.value.show = false;
  }, duration);
}

async function makeApiRequest(requestFunction, operationName) {
  loading.value = true;
  hasError.value = false;
  userFriendlyResult.value = `Executing: ${operationName}...`;

  try {
    const response = await requestFunction();
    showNotification(`${operationName} successful!`, 'success');
    const data = response.data;

    if (operationName.includes('Search') || operationName.includes('Query')) {
      if (data.links && data.links.length > 0) {
        let resultStr = `Query successful! Found ${data.links.length} matching file(s):\n\n`;
        data.links.forEach((link, index) => {
          resultStr += `${index + 1}. ${link}\n`;
        });
        userFriendlyResult.value = resultStr;
      } else {
        userFriendlyResult.value = 'Query complete. No matching files found.';
      }
    } else if (operationName.includes('Login')) {
      token.value = data.token;
      userFriendlyResult.value = `Login successful for user ${email.value}. Token has been acquired.`;
    } else {
      userFriendlyResult.value = data.message || 'Operation completed successfully.';
    }
  } catch (error) {
    hasError.value = true;
    const errorMessage = error.response ? (error.response.data?.error || JSON.stringify(error.response.data)) : error.message;
    userFriendlyResult.value = `Operation Failed: ${errorMessage}`;
    showNotification(`Error: ${errorMessage}`, 'error');
  } finally {
    loading.value = false;
  }
}

const register = () => makeApiRequest(() => axios.post(`${API_GATEWAY_DOMAIN}/register`, { email: email.value, password: password.value }), 'Register User');
const login = () => makeApiRequest(() => axios.post(`${API_GATEWAY_DOMAIN}/login`, { email: email.value, password: password.value }), 'Login');

const searchBySpecies = () => {
  if (!token.value) return showNotification('Please log in first!', 'error');
  makeApiRequest(() => axios.get(`${API_GATEWAY_DOMAIN}/search`, {
    params: { species: speciesToSearch.value },
    headers: { 'Authorization': token.value }
  }), 'Search by Species');
};

const queryByCount = () => {
  if (!token.value) return showNotification('Please log in first!', 'error');
  try {
    const queryBody = JSON.parse(countQuery.value);
    makeApiRequest(() => axios.post(`${API_GATEWAY_DOMAIN}/query-by-count`, queryBody, {
      headers: { 'Authorization': token.value }
    }), 'Search by Count');
  } catch (e) {
    showNotification("Invalid JSON format for tag/count query!", 'error');
  }
};

const handleFileUpload = (event) => {
  fileToUpload.value = event.target.files[0];
  showNotification(`Selected file: ${fileToUpload.value.name}`, 'success');
};

const searchByFile = () => {
  if (!token.value) return showNotification('Please log in first!', 'error');
  if (!fileToUpload.value) return showNotification('Please select a file first!', 'error');
  const formData = new FormData();
  formData.append('file', fileToUpload.value);
  makeApiRequest(() => axios.post(`${API_GATEWAY_DOMAIN}/search-by-file`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      'Authorization': token.value
    }
  }), 'Search by File');
};

const manageTags = (operation) => {
  if (!token.value) return showNotification('Please log in first!', 'error');
  if (!urlToManage.value || !tagsToManage.value) return showNotification('URL and Tag fields cannot be empty!', 'error');
  const body = { url: [urlToManage.value], operation, tags: [tagsToManage.value] };
  makeApiRequest(() => axios.post(`${API_GATEWAY_DOMAIN}/tags/manage`, body, {
    headers: { 'Authorization': token.value }
  }), `Manage Tags (${operation === 1 ? 'Add' : 'Remove'})`);
};

const deleteFile = () => {
  if (!token.value) return showNotification('Please log in first!', 'error');
  if (!urlToDelete.value) return showNotification('URL to delete cannot be empty!', 'error');
  if (!confirm(`ARE YOU SURE you want to permanently delete this file?\n${urlToDelete.value}\nThis action cannot be undone!`)) return;
  const body = { urls: [urlToDelete.value] };
  makeApiRequest(() => axios.post(`${API_GATEWAY_DOMAIN}/files/delete`, body, {
    headers: { 'Authorization': token.value }
  }), 'Delete File');
};
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Fira+Code&display=swap');

:root {
  --primary-color: #007bff;
  --success-color: #28a745;
  --danger-color: #dc3545;
  --dark-color: #343a40;
  --light-color: #f8f9fa;
  --border-color: #dee2e6;
  --font-family: 'Inter', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --mono-font: 'Fira Code', 'SF Mono', Menlo, monospace;
  --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  --border-radius: 8px;
}

body {
  margin: 0;
  font-family: var(--font-family);
  background-color: var(--light-color);
}

#app-container {
  position: relative;
  min-height: 100vh;
  overflow-x: hidden;
}

.background-gradient {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 400px;
  background: linear-gradient(135deg, var(--primary-color), var(--success-color));
  z-index: -1;
}

#app {
  color: var(--dark-color);
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.app-header {
  text-align: center;
  margin-bottom: 3rem;
  color: white;
}
.app-header h1 {
  font-size: 3rem;
  font-weight: 700;
  margin: 0;
}
.app-header p {
  font-size: 1.2rem;
  opacity: 0.9;
}

.card {
  background: white;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 1.5rem 2rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--box-shadow);
  transition: all 0.3s ease;
}

.card h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0;
  padding-bottom: 0.75rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.form-group.vertical {
  flex-direction: column;
  align-items: stretch;
}
.form-group.vertical label {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

input[type="text"], input[type="password"], input[type="email"] {
  padding: 12px 15px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 1rem;
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;
  font-family: var(--font-family);
}
input::placeholder {
  font-style: italic;
  color: #999;
}
input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
}

.file-input {
  border: 2px dashed var(--border-color);
  padding: 1rem;
  text-align: center;
  cursor: pointer;
}

button {
  padding: 12px 20px;
  border: none;
  background-color: var(--primary-color);
  color: white;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.2s;
  white-space: nowrap;
}
button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
button.primary {
  background-color: var(--success-color);
}
.button-group {
  display: flex;
  gap: 1rem;
  justify-content: center;
}
.full-width {
  width: 100%;
}
.button-danger { background-color: var(--danger-color); }
.button-danger:hover:not(:disabled) { background-color: #c82333; }

.token-display { margin-top: 1rem; font-size: 0.9em; color: #666; }
hr { border: none; border-top: 1px solid #eee; margin: 1.5rem 0; }

.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 1rem 1.5rem;
  border-radius: var(--border-radius);
  color: white;
  box-shadow: var(--box-shadow);
  z-index: 1000;
  transform: translateX(120%);
  transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.notification.show {
  transform: translateX(0);
}
.notification.success { background-color: var(--success-color); }
.notification.error { background-color: var(--danger-color); }

@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.loading-spinner {
  border: 5px solid #f3f3f3;
  border-top: 5px solid var(--primary-color);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 20px auto;
}

.result-text-area {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: var(--border-radius);
  padding: 1.5rem;
  min-height: 100px;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: var(--mono-font);
  color: #495057;
  transition: all 0.2s;
}

.result-text-area.error-text {
  background-color: #fbe9e7;
  color: var(--danger-color);
  border-left: 4px solid var(--danger-color);
}
</style>
