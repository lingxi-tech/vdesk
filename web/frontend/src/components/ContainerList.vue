<template>
  <div>
    <div style="display:flex; gap:12px; margin-bottom:16px;">
      <input v-model="newName" placeholder="container name" />
      <input v-model="newImage" placeholder="image (optional)" />
      <button @click="create">Create & Up</button>
    </div>
    <div v-if="loading">loading...</div>
    <div v-for="c in containers" :key="c.name" style="border:1px solid #ddd; padding:12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
      <div style="flex:1;">
        <div style="font-weight:600">{{ c.name }} <span style="color:#666;">({{ c.state }})</span></div>
        <div style="color:#444">Image: {{ c.image }}</div>
        <div style="display:flex; gap:8px; margin-top:8px;">
          <label>Memory: <input v-model="c.memory_size" style="width:110px" /></label>
          <label>Swap: <input v-model="c.swap_size" style="width:110px" /></label>
          <label>GPU IDs: <input v-model="gpuString[c.name]" style="width:120px" /></label>
          <label>Password: <input v-model="c.root_password" style="width:120px" /></label>
        </div>
      </div>
      <div style="display:flex; flex-direction:column; gap:6px; margin-left:12px;">
        <button @click="apply(c, 'memory_size')">Update Memory</button>
        <button @click="applyGpu(c)">Update GPU</button>
        <button @click="apply(c, 'root_password')">Update Password</button>
        <div style="display:flex; gap:6px;">
          <button @click="action(c.name, 'start')">Start</button>
          <button @click="action(c.name, 'stop')">Stop</button>
          <button @click="action(c.name, 'restart')">Restart</button>
          <button @click="action(c.name, 'down')">Down</button>
          <button @click="action(c.name, 'up')">Up</button>
          <button @click="del(c.name)" style="color:#b00">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
export default {
  data() {
    return {
      containers: [],
      loading: false,
      newName: '',
      newImage: '',
      gpuString: {},
    }
  },
  created() {
    this.fetch()
  },
  methods: {
    async fetch() {
      this.loading = true
      try {
        const r = await axios.get('http://localhost:8000/containers')
        this.containers = r.data
        this.containers.forEach(c => { this.gpuString[c.name] = (c.gpu_ids || []).join(',') })
      } finally {
        this.loading = false
      }
    },
    async create() {
      if (!this.newName) return alert('name required')
      await axios.post('http://localhost:8000/containers', { name: this.newName, image: this.newImage })
      this.newName = ''
      this.newImage = ''
      this.fetch()
    },
    async apply(container, key) {
      let value = container[key]
      if (key === 'memory_size' && (!value)) value = '16g'
      await axios.patch(`http://localhost:8000/containers/${container.name}`, { key, value })
      this.fetch()
    },
    async applyGpu(container) {
      const v = this.gpuString[container.name] || ''
      // send as JSON string
      await axios.patch(`http://localhost:8000/containers/${container.name}`, { key: 'gpu_ids', value: JSON.stringify(v.split(',').map(s=>s.trim()).filter(Boolean)) })
      this.fetch()
    },
    async action(name, act) {
      await axios.post(`http://localhost:8000/containers/${name}/action`, null, { params: { action: act } })
      this.fetch()
    },
    async del(name) {
      if (!confirm('Delete container and all data?')) return
      await axios.post(`http://localhost:8000/containers/${name}/action`, null, { params: { action: 'delete' } })
      this.fetch()
    }
  }
}
</script>

<style scoped>
input { padding:6px; border:1px solid #ccc }
button { padding:6px 8px; border:1px solid #bbb; background:#f5f5f5 }
</style>
