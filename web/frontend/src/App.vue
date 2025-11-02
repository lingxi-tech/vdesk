<template>
  <v-app>
    <v-main>
      <v-container>
        <h1>vdesk</h1>
        <ContainerList />
      </v-container>
    </v-main>
  </v-app>
</template>

<script>
import ContainerList from './components/ContainerList.vue'
export default {
  components: { ContainerList }
}
</script>
