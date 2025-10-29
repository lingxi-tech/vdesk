<template>
  <div style="font-family: Arial, Helvetica, sans-serif; padding: 24px;">
    <h1>vdesk container manager</h1>
    <ContainerList />
  </div>
</template>

<script>
import ContainerList from './components/ContainerList.vue'
export default { components: { ContainerList } }
</script>
