<template>
  <div id="app">
    <nav class="navbar">
      <router-link to="/">文本列表</router-link>
      <router-link to="/import">导入</router-link>
    </nav>
    <main>
      <router-view />
    </main>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.navbar {
  background: #2c3e50;
  padding: 1rem;
  display: flex;
  gap: 1rem;
}
.navbar a {
  color: white;
  text-decoration: none;
}
.navbar a.router-link-active {
  color: #42b883;
}
main {
  padding: 1rem;
}
</style>
