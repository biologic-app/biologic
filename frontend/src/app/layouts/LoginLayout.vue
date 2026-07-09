<template>
  <div class="min-h-screen bg-default">
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute inset-x-0 top-0 h-125 bg-linear-to-b from-primary/20 via-primary/5 to-transparent" />
      <div class="absolute -left-24 top-10 size-96 rounded-full bg-primary/30 blur-[120px]" />
      <div class="absolute -right-16 top-1/4 size-125 rounded-full bg-primary/20 blur-[140px]" />
      <div class="absolute inset-x-0 bottom-0 h-80 bg-linear-to-t from-primary/15 via-transparent to-transparent" />
      <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 size-150 bg-primary/[0.07] blur-[100px] rounded-full" />
    </div>

    <div class="relative mx-auto flex min-h-screen w-full max-w-7xl items-center px-6 py-12 lg:px-10">
      <RouterView />
    </div>
  </div>
</template>
