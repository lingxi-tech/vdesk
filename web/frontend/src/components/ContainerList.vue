<template>
  <v-container>
    <v-row>
      <v-col cols="12">
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
                  <v-btn color="primary" type="submit">Create</v-btn>
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
                <v-btn icon small @click="action(item.name, 'start')" :title="'Start ' + item.name">
                  <v-icon>mdi-play</v-icon>
                </v-btn>
                <v-btn icon small @click="action(item.name, 'stop')" :title="'Stop ' + item.name">
                  <v-icon>mdi-stop</v-icon>
                </v-btn>
                <v-btn icon small @click="action(item.name, 'restart')" :title="'Restart ' + item.name">
                  <v-icon>mdi-reload</v-icon>
                </v-btn>
                <v-btn icon small color="error" @click="del(item.name)" :title="'Delete ' + item.name">
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
                <v-btn icon small @click="openModify(item)" :title="'Modify ' + item.name">
                  <v-icon>mdi-pencil</v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

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
                <v-text-field v-model="modifyForm.root_password" label="Root Password" type="password" />
              </v-col>
              <v-col cols="12">
                <v-select v-model="modifyForm.gpus" :items="gpuItems" label="GPU IDs" multiple chips />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn text @click="modifyDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="submitModify">Apply & Restart</v-btn>
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
      snackbar: { show: false, message: '', color: 'info' }
    }
  },
  mounted() {
    this.load()
    this.loadImages()
  },
  methods: {
    async load() {
      try {
        const res = await axios.get('/api/containers')
        this.containers = res.data
      } catch (e) {
        this.handleError(e, 'Failed to load containers')
      }
    },
    async loadImages() {
      try {
        const res = await axios.get('/api/images')
        this.images = res.data
        if (!this.form.image && this.images.length) this.form.image = this.images[0]
      } catch (e) {
        this.handleError(e, 'Failed to load images')
      }
    },
    async create() {
      try {
        await axios.post('/api/containers', this.form)
        await this.load()
        this.snackbar = { show: true, message: 'Created', color: 'success' }
      } catch (e) {
        this.handleError(e, 'Failed to create')
      }
    },
    async action(name, act) {
      try {
        await axios.post(`/api/containers/${name}/action`, null, { params: { action: act } })
        await this.load()
        this.snackbar = { show: true, message: act + ' executed', color: 'success' }
      } catch (e) {
        this.handleError(e, `Failed to ${act}`)
      }
    },
    async del(name) {
      try {
        if (!confirm('delete ' + name + '?')) return
        await axios.post(`/api/containers/${name}/action`, null, { params: { action: 'delete' } })
        await this.load()
        this.snackbar = { show: true, message: 'Deleted', color: 'success' }
      } catch (e) {
        this.handleError(e, 'Failed to delete')
      }
    },
    openModify(item) {
      this.modifyTarget = item
      this.modifyForm = { gpus: item.gpus || [], swap: item.swap || '', root_password: '', comment: item.comment || '' }
      this.modifyDialog = true
    },
    async submitModify() {
      try {
        await axios.put(`/api/containers/${this.modifyTarget.name}`, this.modifyForm)
        this.modifyDialog = false
        await this.load()
        this.snackbar = { show: true, message: 'Modified and restarted', color: 'success' }
      } catch (e) {
        this.handleError(e, 'Failed to modify')
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
