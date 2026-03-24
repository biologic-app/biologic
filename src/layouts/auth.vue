<template>
  <div class="min-h-screen bg-default">
    <div class="absolute inset-0 overflow-hidden">
      <div class="absolute inset-x-0 top-0 h-80 bg-gradient-to-b from-primary/15 via-primary/5 to-transparent" />
      <div class="absolute -left-16 top-24 size-64 rounded-full bg-primary/10 blur-3xl" />
      <div class="absolute right-0 top-1/3 size-80 rounded-full bg-primary/10 blur-3xl" />
      <div class="absolute inset-x-0 bottom-0 h-56 bg-gradient-to-t from-elevated/60 to-transparent" />
    </div>

    <div class="relative mx-auto flex min-h-screen w-full max-w-7xl items-center px-6 py-12 lg:px-10">
      <RouterView />
    </div>
  </div>
</template>
