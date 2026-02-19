<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { onWsMessage, sendWsMessage } from "../setup/main";

const props = withDefaults(
  defineProps<{
    pollId: string;
    question: string;
    options: string[];
    maxChoices?: number;
  }>(),
  { maxChoices: 1 },
);

const selected = ref<string[]>([]);
const hasVoted = ref(false);
const votes = ref<Record<string, number>>({});

const totalVotes = computed(() =>
  Object.values(votes.value).reduce((sum, v) => sum + v, 0),
);

function toggleOption(opt: string) {
  if (hasVoted.value) return;
  const idx = selected.value.indexOf(opt);
  if (idx >= 0) {
    selected.value.splice(idx, 1);
  } else if (selected.value.length < props.maxChoices) {
    selected.value.push(opt);
  }
}

function submitVote() {
  if (selected.value.length === 0 || hasVoted.value) return;
  sendWsMessage({
    type: "poll_vote",
    pollId: props.pollId,
    choices: selected.value,
    options: props.options,
    maxChoices: props.maxChoices,
  });
  hasVoted.value = true;
}

let unsubscribe: (() => void) | null = null;

onMounted(() => {
  unsubscribe = onWsMessage((data) => {
    if (data.type === "poll_state" && data.pollId === props.pollId) {
      votes.value = (data.votes as Record<string, number>) || {};
    }
  });
});

onUnmounted(() => {
  unsubscribe?.();
});
</script>

<template>
  <div class="poll-container">
    <h3 class="poll-question">{{ question }}</h3>
    <p v-if="maxChoices > 1" class="poll-hint">
      最大{{ maxChoices }}つまで選択できます
    </p>

    <div class="poll-options">
      <button
        v-for="opt in options"
        :key="opt"
        class="poll-option"
        :class="{
          selected: selected.includes(opt),
          disabled: hasVoted,
        }"
        @click="toggleOption(opt)"
      >
        <span class="poll-check">{{
          selected.includes(opt) ? "✓" : ""
        }}</span>
        <span class="poll-label">{{ opt }}</span>
        <span v-if="hasVoted && votes[opt] != null" class="poll-count">
          {{ votes[opt] }}票
        </span>
      </button>
    </div>

    <button
      v-if="!hasVoted"
      class="poll-submit"
      :disabled="selected.length === 0"
      @click="submitVote"
    >
      投票する
    </button>

    <div v-if="hasVoted" class="poll-results">
      <p class="poll-voted-msg">投票済み（計{{ totalVotes }}票）</p>
      <div v-for="opt in options" :key="opt" class="poll-bar-row">
        <span class="poll-bar-label">{{ opt }}</span>
        <div class="poll-bar-track">
          <div
            class="poll-bar-fill"
            :style="{
              width:
                totalVotes > 0
                  ? `${((votes[opt] || 0) / totalVotes) * 100}%`
                  : '0%',
            }"
          />
        </div>
        <span class="poll-bar-value">{{ votes[opt] || 0 }}</span>
      </div>
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
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: 2px solid #555;
  border-radius: 8px;
  background: transparent;
  color: #eee;
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.poll-option:hover:not(.disabled) {
  border-color: #4ec9b0;
}

.poll-option.selected {
  border-color: #4ec9b0;
  background: rgba(78, 201, 176, 0.15);
}

.poll-option.disabled {
  cursor: default;
  opacity: 0.8;
}

.poll-check {
  width: 1.2rem;
  text-align: center;
  color: #4ec9b0;
  font-weight: bold;
}

.poll-label {
  flex: 1;
  text-align: left;
}

.poll-count {
  color: #aaa;
  font-size: 0.9rem;
}

.poll-submit {
  margin-top: 0.5rem;
  padding: 0.6rem 2rem;
  border: none;
  border-radius: 8px;
  background: #4ec9b0;
  color: #1a1a2e;
  font-size: 1.1rem;
  font-weight: bold;
  cursor: pointer;
  transition: opacity 0.2s;
}

.poll-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.poll-submit:hover:not(:disabled) {
  opacity: 0.85;
}

.poll-results {
  width: 100%;
  max-width: 500px;
}

.poll-voted-msg {
  text-align: center;
  color: #4ec9b0;
  font-size: 1rem;
  margin: 0.5rem 0;
}

.poll-bar-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}

.poll-bar-label {
  width: 140px;
  text-align: right;
  font-size: 0.9rem;
  color: #ccc;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.poll-bar-track {
  flex: 1;
  height: 20px;
  background: #333;
  border-radius: 4px;
  overflow: hidden;
}

.poll-bar-fill {
  height: 100%;
  background: #4ec9b0;
  border-radius: 4px;
  transition: width 0.4s ease;
}

.poll-bar-value {
  width: 2.5rem;
  text-align: right;
  font-size: 0.9rem;
  color: #aaa;
}
</style>
