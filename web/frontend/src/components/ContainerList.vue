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
                <v-col cols="12">
                  <v-text-field v-model="form.comment" label="Comment" />
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
                <v-btn icon small @click="action(item.name, 'start')" :title="'Start ' + item.name" :disabled="loading">
                  <v-icon>mdi-play</v-icon>
                </v-btn>
                <v-btn icon small @click="action(item.name, 'stop')" :title="'Stop ' + item.name" :disabled="loading">
                  <v-icon>mdi-stop</v-icon>
                </v-btn>
                <v-btn icon small @click="action(item.name, 'restart')" :title="'Restart ' + item.name" :disabled="loading">
                  <v-icon>mdi-reload</v-icon>
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
        gpus: [],
      },
      headers: [
        { title: 'Name', key: 'name', value: 'name' },
        { title: 'Port', key: 'port', value: 'port' },
        { title: 'Image', key: 'image', value: 'image' },
        { title: 'Memory', key: 'memory', value: 'memory' },
        { title: 'CPUs', key: 'cpus', value: 'cpus' },
        { title: 'GPUs', key: 'gpus', value: 'gpus' },
        { title: 'Comment', key: 'comment', value: 'comment' },
        { title: 'State', key: 'state', value: 'state' },
        { title: 'Actions', key: 'actions', value: 'actions' },
      ],
      modifyDialog: false,
      modifyTarget: null,
      modifyForm: { gpus: [], swap: '', root_password: '', comment: '' },
      gpuItems: Array.from({ length: 32 }, (_, i) => i),
      snackbar: { show: false, message: '', color: 'info' },
      loginDialog: false,
      loginForm: { username: '', password: '' },
      changePasswordDialog: false,
      changePasswordForm: { old_password: '', new_password: '' },
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
       this.modifyForm = { gpus: gpus, swap: item.swap || '', root_password: '', comment: item.comment || '' }
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
