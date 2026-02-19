<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { onWsMessage, sendWsMessage } from "../setup/main";
import { connectionStatus, ConnectionStatusEnum } from "../setup/connectionState";

function getVisitorId(): string {
  const key = "slide_visitor";
  const match = document.cookie.match(new RegExp(`(?:^|; )${key}=([^;]*)`));
  if (match) return match[1];
  const id = crypto.randomUUID();
  document.cookie = `${key}=${id}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Strict`;
  return id;
}

const visitorId = getVisitorId();

interface PollOption {
  id: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    pollId: string;
    options: PollOption[];
    maxChoices?: number;
  }>(),
  { maxChoices: 1 },
);

const selected = ref<Set<string>>(new Set());
const loading = ref<Set<string>>(new Set());
const votes = ref<Record<string, number>>({});

const remainingChoices = computed(
  () => props.maxChoices - selected.value.size - loading.value.size,
);

const totalVotes = computed(() =>
  Object.values(votes.value).reduce((sum, v) => sum + v, 0),
);

function votePercent(id: string): number {
  if (totalVotes.value === 0) return 0;
  return ((votes.value[id] || 0) / totalVotes.value) * 100;
}

function selectOption(id: string) {
  if (loading.value.has(id)) return;

  if (selected.value.has(id)) {
    // Unvote: remove from selected, add to loading
    const next = new Set(selected.value);
    next.delete(id);
    selected.value = next;
    loading.value = new Set([...loading.value, id]);
    const sent = sendWsMessage({
      type: "poll_unvote",
      pollId: props.pollId,
      visitorId,
      choice: id,
    });
    if (!sent) {
      selected.value = new Set([...selected.value, id]);
      const rollback = new Set(loading.value);
      rollback.delete(id);
      loading.value = rollback;
    }
    return;
  }

  if (remainingChoices.value <= 0) return;

  loading.value = new Set([...loading.value, id]);
  const sent = sendWsMessage({
    type: "poll_vote",
    pollId: props.pollId,
    visitorId,
    choice: id,
    options: props.options.map((o) => o.id),
    maxChoices: props.maxChoices,
  });
  if (!sent) {
    const rollback = new Set(loading.value);
    rollback.delete(id);
    loading.value = rollback;
  }
}

function fetchPollState() {
  sendWsMessage({ type: "poll_get", pollId: props.pollId, visitorId });
}

let unsubscribe: (() => void) | null = null;
let stopWatch: (() => void) | null = null;

onMounted(() => {
  unsubscribe = onWsMessage((data) => {
    if (data.type === "poll_state" && data.pollId === props.pollId) {
      votes.value = (data.votes as Record<string, number>) || {};
      if (Array.isArray(data.myChoices)) {
        selected.value = new Set(data.myChoices as string[]);
        loading.value = new Set();
      }
    }
  });

  // Fetch initial state when connected (or immediately if already connected)
  if (connectionStatus.value === ConnectionStatusEnum.Connected) {
    fetchPollState();
  }
  stopWatch = watch(connectionStatus, (status) => {
    if (status === ConnectionStatusEnum.Connected) {
      fetchPollState();
    }
  });
});

onUnmounted(() => {
  unsubscribe?.();
  stopWatch?.();
});
</script>

<template>
  <div class="poll-container">
    <p v-if="maxChoices > 1" class="poll-hint">
      最大{{ maxChoices }}つ選択できます（残り{{ remainingChoices }}）
    </p>

    <div class="poll-options">
      <button
        v-for="opt in options"
        :key="opt.id"
        class="poll-option"
        :class="{
          selected: selected.has(opt.id),
          loading: loading.has(opt.id),
          disabled: selected.has(opt.id) || loading.has(opt.id) || remainingChoices <= 0,
        }"
        @click="selectOption(opt.id)"
      >
        <div
          class="poll-option-fill"
          :style="{ width: `${votePercent(opt.id)}%` }"
        />
        <span class="poll-option-content">
          <span class="poll-check">
            <span v-if="loading.has(opt.id)" class="poll-spinner" />
            <template v-else>{{ selected.has(opt.id) ? "✓" : "" }}</template>
          </span>
          <span class="poll-label">{{ opt.label }}</span>
          <span class="poll-count">
            {{ votes[opt.id] || 0 }}
          </span>
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.poll-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
}

.poll-hint {
  font-size: 0.9rem;
  color: #aaa;
  margin: 0;
}

.poll-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  max-width: 500px;
}

.poll-option {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 0.6rem 1rem;
  border: 2px solid #555;
  border-radius: 8px;
  background: transparent;
  color: #eee;
  font-size: 1.1rem;
  cursor: pointer;
  transition: border-color 0.2s;
}

.poll-option:hover:not(.disabled) {
  border-color: #4ec9b0;
}

.poll-option.selected {
  border-color: #4ec9b0;
}

.poll-option.disabled {
  cursor: default;
}

.poll-option-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: rgba(78, 201, 176, 0.2);
  border-radius: 6px;
  transition: width 0.4s ease;
  pointer-events: none;
}

.poll-option-content {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  z-index: 1;
}

.poll-check {
  width: 1.2rem;
  text-align: center;
  color: #4ec9b0;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.poll-spinner {
  width: 0.9rem;
  height: 0.9rem;
  border: 2px solid rgba(78, 201, 176, 0.3);
  border-top-color: #4ec9b0;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.poll-label {
  flex: 1;
  text-align: left;
}

.poll-count {
  color: #aaa;
  font-size: 0.9rem;
}
</style>
