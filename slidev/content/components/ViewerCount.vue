<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { onWsMessage, sendWsMessage } from "../setup/main";
import { connectionStatus, ConnectionStatusEnum } from "../setup/connectionState";

const count = ref(0);

function fetchViewerCount() {
  sendWsMessage({ type: "viewer_count" });
}

let unsubscribe: (() => void) | null = null;
let stopWatch: (() => void) | null = null;

onMounted(() => {
  unsubscribe = onWsMessage((data) => {
    if (data.type === "viewer_count" && typeof data.count === "number") {
      count.value = data.count;
    }
  });

  if (connectionStatus.value === ConnectionStatusEnum.Connected) {
    fetchViewerCount();
  }
  stopWatch = watch(connectionStatus, (status) => {
    if (status === ConnectionStatusEnum.Connected) {
      fetchViewerCount();
    }
  });
});

onUnmounted(() => {
  unsubscribe?.();
  stopWatch?.();
});
</script>

<template>
  <div class="viewer-count">
    <carbon:user-multiple class="viewer-count-icon" />
    <span class="viewer-count-number">{{ count }}</span>
  </div>
</template>

<style scoped>
.viewer-count {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.5);
  color: #4ec9b0;
  font-size: 0.9rem;
  font-weight: 600;
  backdrop-filter: blur(4px);
}

.viewer-count-icon {
  font-size: 1rem;
}

.viewer-count-number {
  min-width: 1ch;
  text-align: center;
}
</style>
