<template>
  <v-container>
    <v-overlay :absolute="true" :value="loading">
      <v-progress-circular indeterminate size="64" color="primary" />
    </v-overlay>
     <v-row>
      <v-col cols="12">
        <v-btn small @click="openLogin" v-if="!auth.token">Login</v-btn>
        <template v-else>
          <v-btn small @click="openChangePassword">Change Password</v-btn>
          <v-btn small @click="logout">Logout ({{ auth.user }})</v-btn>
        </template>
       <v-card class="pa-4">
          <v-card-title>Create Container</v-card-title>
          <v-card-text>
            <v-form ref="createForm" @submit.prevent="create">
              <v-row>
                <v-col cols="3">
                  <v-text-field v-model="form.name" label="6-digit name" />
                </v-col>
                <v-col cols="3">
                  <v-select :items="images" v-model="form.image" label="Image" />
                </v-col>
                <v-col cols="2">
                  <v-text-field v-model.number="form.cpus" type="number" min="1" max="32" label="CPUs" />
                </v-col>
                <v-col cols="2">
                  <v-text-field v-model="form.memory" label="Memory (e.g. 4g)" />
                </v-col>
                <v-col cols="2">
                  <v-select v-model="form.gpus" :items="gpuItems" label="GPU IDs" multiple chips dense />
                </v-col>
              </v-row>

              <v-row>
                <v-col cols="9">
                  <v-text-field v-model="form.comment" label="Comment" />
                </v-col>
                <v-col cols="3">
                  <v-text-field v-model="form.shm_size" label="shm_size (e.g. 32gb)" />
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="12">
                  <v-btn color="primary" type="submit" :disabled="loading">Create</v-btn>
                </v-col>
              </v-row>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-6">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Containers
          </v-card-title>
          <v-card-text>
            <v-data-table :items="containers" :headers="headers" class="elevation-1">
              <template #item.actions="{ item }">
                <!-- show Start only when container is not running -->
                <v-btn v-if="!isRunning(item)" icon small @click="action(item.name, 'start')" :title="'Start ' + item.name" :disabled="loading">
                  <v-icon>mdi-play</v-icon>
                </v-btn>
                <!-- show Stop only when container is running -->
                <v-btn v-if="isRunning(item)" icon small @click="action(item.name, 'stop')" :title="'Stop ' + item.name" :disabled="loading">
                  <v-icon>mdi-stop</v-icon>
                </v-btn>
                <!-- show Restart only when running -->
                <v-btn v-if="isRunning(item)" icon small @click="action(item.name, 'restart')" :title="'Restart ' + item.name" :disabled="loading">
                  <v-icon>mdi-reload</v-icon>
                </v-btn>
                <!-- Exec command button -->
                <v-btn icon small @click="openExec(item)" :title="'Exec in ' + item.name" :disabled="loading">
                  <v-icon>mdi-console</v-icon>
                </v-btn>
                <v-btn icon small @click="openLogs(item)" :title="'Logs ' + item.name" :disabled="loading">
                  <v-icon>mdi-history</v-icon>
                </v-btn>
                <v-btn icon small color="error" @click="del(item.name)" :title="'Delete ' + item.name" :disabled="loading">
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
                <v-btn icon small @click="openModify(item)" :title="'Modify ' + item.name" :disabled="loading">
                  <v-icon>mdi-pencil</v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card class="pa-4 mb-4">
      <v-card-title>Host Resources</v-card-title>
      <v-card-text>
        <div>CPUs: {{ host.cpus }}</div>
        <div>Memory: {{ host.memory_gb }} GB</div>
        <div>GPUs:
          <template v-if="host.gpus.length">
            <ul style="margin:0;padding-left:1rem">
              <li v-for="g in host.gpus" :key="g.id">{{ g.id }} - {{ g.name || 'unknown' }}</li>
            </ul>
          </template>
          <span v-else>none</span>
        </div>
      </v-card-text>
    </v-card>

    <v-dialog v-model="modifyDialog" max-width="600">
      <v-card>
        <v-card-title>Modify {{ modifyTarget?.name }}</v-card-title>
        <v-card-text>
          <v-form>
            <v-row>
              <v-col cols="12">
                <v-text-field v-model="modifyForm.comment" label="Comment" />
              </v-col>
              <v-col cols="12">
                <v-text-field v-model="modifyForm.swap" label="Swap Size (e.g. 2g)" />
              </v-col>
              <v-col cols="12">
                <v-text-field v-model="modifyForm.root_password" label="Root Password" type="text" />
              </v-col>
              <v-col cols="12">
                <v-select v-model="modifyForm.gpus" :items="gpuItems" label="GPU IDs" multiple chips />
              </v-col>
              <v-col cols="12">
                <v-text-field v-model="modifyForm.shm_size" label="shm_size (e.g. 32gb)" />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="modifyDialog = false" :disabled="loading">Cancel</v-btn>
          <v-btn color="primary" @click="submitModify" :disabled="loading">Apply & Restart</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="loginDialog" max-width="400">
      <v-card>
        <v-card-title>Login</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field v-model="loginForm.username" label="Username" />
            <v-text-field v-model="loginForm.password" label="Password" type="password" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="loginDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="doLogin">Login</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="changePasswordDialog" max-width="400">
      <v-card>
        <v-card-title>Change Password</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field v-model="changePasswordForm.old_password" label="Current Password" type="password" />
            <v-text-field v-model="changePasswordForm.new_password" label="New Password" type="password" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="changePasswordDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="submitChangePassword" :disabled="loading">Change</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="execDialog" max-width="700">
      <v-card>
        <v-card-title>Run command in {{ execTarget?.name }}</v-card-title>
        <v-card-text>
          <v-form>
            <v-textarea v-model="execForm.cmd" label="Bash command" rows="3" auto-grow />
            <div v-if="execResult">
              <h4>Result (rc={{ execResult.returncode }})</h4>
              <pre style="white-space:pre-wrap; background:#f5f5f5; padding:8px">{{ execResult.stdout }}{{ execResult.stderr ? '\nERR:\n' + execResult.stderr : '' }}</pre>
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="execDialog = false" :disabled="loading">Close</v-btn>
          <v-btn color="primary" @click="submitExec" :disabled="loading">Run</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="logsDialog" max-width="800">
      <v-card>
        <v-card-title>Command logs for {{ logsTarget?.name }}</v-card-title>
        <v-card-text>
          <div v-if="logsList.length === 0">No logs</div>
          <div v-else>
            <v-list dense>
              <v-list-item v-for="l in logsList" :key="l.id">
                <v-list-item-content>
                  <div style="font-size:0.9rem;color:#666">{{ l.timestamp }} — {{ l.user || 'unknown' }}</div>
                  <div style="font-weight:600">$ {{ l.cmd }}</div>
                  <pre style="white-space:pre-wrap; background:#f7f7f7; padding:6px; margin-top:6px">{{ l.stdout }}{{ l.stderr ? '\nERR:\n' + l.stderr : '' }}</pre>
                </v-list-item-content>
              </v-list-item>
            </v-list>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="logsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" top>
      {{ snackbar.message }}
      <template #actions>
        <v-btn text @click="snackbar.show = false">Close</v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script>
import axios from 'axios'
export default {
  data() {
    return {
      containers: [],
      images: [],
      host: { cpus: 0, memory_gb: 0, gpus: [] },
      loading: false,
      auth: { token: localStorage.getItem('vdesk_token') || null, user: localStorage.getItem('vdesk_user') || null },
      form: {
        name: '',
        image: '',
        cpus: 1,
        memory: '2g',
        shm_size: '',
        gpus: [],
      },
      headers: [
        { title: 'Name', key: 'name', value: 'name' },
        { title: 'Port', key: 'port', value: 'port' },
        { title: 'Image', key: 'image', value: 'image' },
        { title: 'Memory', key: 'memory', value: 'memory' },
        { title: 'Shm', key: 'shm_size', value: 'shm_size' },
        { title: 'CPUs', key: 'cpus', value: 'cpus' },
        { title: 'GPUs', key: 'gpus', value: 'gpus' },
        { title: 'Comment', key: 'comment', value: 'comment' },
        { title: 'State', key: 'state', value: 'state' },
        { title: 'Actions', key: 'actions', value: 'actions' },
      ],
      modifyDialog: false,
      modifyTarget: null,
      modifyForm: { gpus: [], swap: '', root_password: '', comment: '', shm_size: '' },
      gpuItems: Array.from({ length: 32 }, (_, i) => i),
      snackbar: { show: false, message: '', color: 'info' },
      loginDialog: false,
      loginForm: { username: '', password: '' },
      changePasswordDialog: false,
      changePasswordForm: { old_password: '', new_password: '' },
      execDialog: false,
      execTarget: null,
      execForm: { cmd: '' },
      execResult: null,
      logsDialog: false,
      logsTarget: null,
      logsList: [],
    }
  },
  mounted() {
    if (this.auth.token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${this.auth.token}`
      this.load()
      this.loadImages()
      this.loadHost()
    } else {
      // prompt for login before loading protected resources
      this.openLogin()
    }
  },
  methods: {
    isRunning(item) {
      const s = (item && item.state) ? String(item.state).trim().toLowerCase() : ''
      if (!s) return false
      // treat these statuses as 'running' for UI purposes, but exclude 'paused'
      const runningIndicators = ['up', 'running', 'restarting', 'healthy']
      return runningIndicators.some(k => s.includes(k))
    },
    openLogin() {
      this.loginDialog = true
      this.loginForm = { username: '', password: '' }
    },
    openChangePassword() {
      this.changePasswordDialog = true
      this.changePasswordForm = { old_password: '', new_password: '' }
    },
    async doLogin() {
      try {
        const res = await axios.post('/api/login', this.loginForm)
        this.auth.token = res.data.token
        this.auth.user = res.data.user
        localStorage.setItem('vdesk_token', this.auth.token)
        localStorage.setItem('vdesk_user', this.auth.user)
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.auth.token}`
        this.loginDialog = false
        this.snackbar = { show: true, message: 'Logged in', color: 'success' }
        // reload protected data
        this.load()
        this.loadImages()
      } catch (e) {
        this.handleError(e, 'Login failed')
      }
    },
    logout() {
      localStorage.removeItem('vdesk_token')
      localStorage.removeItem('vdesk_user')
      delete axios.defaults.headers.common['Authorization']
      this.auth = { token: null, user: null }
      this.snackbar = { show: true, message: 'Logged out', color: 'info' }
    },
    async load() {
      this.loading = true
       try {
         const res = await axios.get('/api/containers')
         this.containers = res.data
       } catch (e) {
         this.handleError(e, 'Failed to load containers')
       } finally {
         this.loading = false
       }
     },
     async loadImages() {
      this.loading = true
       try {
         const res = await axios.get('/api/images')
         this.images = res.data
         if (!this.form.image && this.images.length) this.form.image = this.images[0]
       } catch (e) {
         this.handleError(e, 'Failed to load images')
       } finally {
         this.loading = false
       }
     },
     async loadHost() {
      try {
        const res = await axios.get('/api/host')
        const d = res.data || {}
        const memBytes = d.memory_bytes || 0
        // backend now returns gpus as list of objects {id, name}
        this.host = { cpus: d.cpus || 0, memory_gb: memBytes ? Math.round(memBytes / (1024*1024*1024) ) : 0, gpus: d.gpus || [] }
      } catch (e) {
        console.warn('failed to load host info', e)
      }
     },
     async create() {
      this.loading = true
      try {
        // normalize and dedupe GPU ids before sending
        const g = Array.from(new Set((this.form.gpus || []).map(x => Number(x))))
        const payload = { ...this.form, gpus: g }
        await axios.post('/api/containers', payload)
        await this.load()
        this.snackbar = { show: true, message: 'Created', color: 'success' }
      } catch (e) {
        this.handleError(e, 'Failed to create')
      } finally {
        this.loading = false
      }
     },
     async action(name, act) {
      this.loading = true
      try {
        await axios.post(`/api/containers/${name}/action`, null, { params: { action: act } })
        await this.load()
        this.snackbar = { show: true, message: act + ' executed', color: 'success' }
      } catch (e) {
        this.handleError(e, `Failed to ${act}`)
      } finally {
        this.loading = false
      }
     },
     async del(name) {
      if (!confirm('delete ' + name + '?')) return
      this.loading = true
      try {
        await axios.post(`/api/containers/${name}/action`, null, { params: { action: 'delete' } })
        await this.load()
        this.snackbar = { show: true, message: 'Deleted', color: 'success' }
      } catch (e) {
        this.handleError(e, 'Failed to delete')
      } finally {
        this.loading = false
      }
     },
     openModify(item) {
       // normalize GPU ids to numbers so v-select matches correctly
       const gpus = (item.gpus || []).map(x => Number(x))
       this.modifyTarget = item
       this.modifyForm = {
         gpus: gpus,
         swap: item.swap || item.SWAP_SIZE || '',
         root_password: item.root_password || item.ROOTPASSWORD || '',
         comment: item.comment || '',
         shm_size: item.shm_size || ''
       }
       this.modifyDialog = true
     },
     async submitModify() {
      this.loading = true
      try {
        // normalize and deduplicate GPU ids before sending
        const g = Array.from(new Set((this.modifyForm.gpus || []).map(x => Number(x))))
        const payload = { ...this.modifyForm, gpus: g }
        await axios.put(`/api/containers/${this.modifyTarget.name}`, payload)
        this.modifyDialog = false
        await this.load()
        this.snackbar = { show: true, message: 'Modified and restarted', color: 'success' }
      } catch (e) {
        this.handleError(e, 'Failed to modify')
      } finally {
        this.loading = false
      }
     },
     async submitChangePassword() {
      if (!this.changePasswordForm.old_password || !this.changePasswordForm.new_password) {
        this.snackbar = { show: true, message: 'Both fields required', color: 'error' }
        return
      }
      this.loading = true
      try {
        const res = await axios.post('/api/change-password', this.changePasswordForm)
        this.snackbar = { show: true, message: res.data?.message || 'Password changed', color: 'success' }
        // Invalidate local session and require re-login
        this.logout()
        this.changePasswordDialog = false
      } catch (e) {
        this.handleError(e, 'Failed to change password')
      } finally {
        this.loading = false
      }
    },
    openExec(item) {
      this.execTarget = item
      this.execForm = { cmd: '' }
      this.execResult = null
      this.execDialog = true
    },
    async openLogs(item) {
      this.logsTarget = item
      this.logsList = []
      this.logsDialog = true
      this.loading = true
      try {
        const res = await axios.get(`/api/containers/${item.name}/exec-logs`)
        this.logsList = res.data || []
      } catch (e) {
        this.handleError(e, 'Failed to load logs')
      } finally {
        this.loading = false
      }
    },
    async submitExec() {
      if (!this.execTarget || !this.execForm.cmd) return
      this.loading = true
      try {
        // open websocket to stream output
        const token = this.auth.token
        // In development Vite runs on port 5173 and typically does not proxy websocket upgrades to the backend.
        // Connect directly to backend on port 8000 when running on the dev server.
        const proto = location.protocol === 'https:' ? 'wss' : 'ws'
        let hostForWs = location.host
        if (location.port === '5173') {
          hostForWs = `${location.hostname}:8000`
        }
        const wsUrl = `${proto}://${hostForWs}/api/containers/${this.execTarget.name}/exec-ws?token=${encodeURIComponent(token)}`
         const ws = new WebSocket(wsUrl)
         this.execResult = { stdout: '', stderr: '', returncode: null }
         ws.onopen = () => {
           ws.send(JSON.stringify({ cmd: this.execForm.cmd }))
         }
         ws.onmessage = (ev) => {
           try {
             const msg = JSON.parse(ev.data)
             if (msg.type === 'stdout') {
               this.execResult.stdout += msg.data
             } else if (msg.type === 'stderr') {
               this.execResult.stderr += msg.data
             } else if (msg.type === 'exit') {
               this.execResult.returncode = msg.returncode
               this.snackbar = { show: true, message: 'Command finished', color: 'success' }
               ws.close()
             } else if (msg.type === 'error') {
               // if auth error, prompt for login
               if (msg.detail && String(msg.detail).toLowerCase().includes('unauthorized')) {
                 this.snackbar = { show: true, message: 'Authorization failed; please login again', color: 'error' }
                 this.logout()
                 this.openLogin()
               } else {
                 this.handleError({ response: { data: { detail: msg.detail } } }, 'Exec error')
               }
               ws.close()
             }
           } catch (e) {
             console.error('invalid ws msg', e)
           }
         }
         ws.onerror = (e) => {
          console.error('ws error', e)
          this.snackbar = { show: true, message: 'WebSocket error connecting to backend', color: 'error' }
         }
      } catch (e) {
        this.handleError(e, 'Failed to exec')
      } finally {
        this.loading = false
      }
    },
     handleError(e, defaultMsg) {
      const msg = e.response?.data?.detail || e.message || defaultMsg
      this.snackbar = { show: true, message: msg, color: 'error' }
      console.error(e)
    }
  }
}
</script>

<style scoped>
.v-data-table th { text-align: left }
</style>
