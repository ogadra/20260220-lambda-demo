<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { onWsMessage, sendWsMessage } from "../setup/main";
import { connectionStatus, ConnectionStatusEnum } from "../setup/connectionState";

interface PollOption {
  id: string;
  label: string;
}

const props = withDefaults(
  defineProps<{
    pollId: string;
    question: string;
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
  if (selected.value.has(id)) return;
  if (loading.value.has(id)) return;
  if (remainingChoices.value <= 0) return;

  loading.value = new Set([...loading.value, id]);
  sendWsMessage({
    type: "poll_vote",
    pollId: props.pollId,
    choice: id,
    options: props.options.map((o) => o.id),
    maxChoices: props.maxChoices,
  });
}

function fetchPollState() {
  sendWsMessage({ type: "poll_get", pollId: props.pollId });
}

let unsubscribe: (() => void) | null = null;
let stopWatch: (() => void) | null = null;

onMounted(() => {
  unsubscribe = onWsMessage((data) => {
    if (data.type === "poll_state" && data.pollId === props.pollId) {
      votes.value = (data.votes as Record<string, number>) || {};
      // Move loading items to selected on response
      if (loading.value.size > 0) {
        selected.value = new Set([...selected.value, ...loading.value]);
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
    <h3 class="poll-question">{{ question }}</h3>
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
          <span v-if="totalVotes > 0" class="poll-count">
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
  padding: 1.5rem;
}

.poll-question {
  font-size: 1.6rem;
  color: #4ec9b0;
  margin: 0;
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
  padding: 0.75rem 1rem;
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
