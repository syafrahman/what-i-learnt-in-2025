<script lang="ts" context="module">
  export const ssr = false;
</script>

<script lang="ts">
  import { onMount } from 'svelte';

  type Submission = {
    text: string;
    name: string | null;
    date: string | null;
  };

  const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

  let text = '';
  let name = '';
  let feed: Submission[] = [];
  let feedError = '';
  let loading = false;
  let successMessage = '';
  let errorMessage = '';
  let buttonDisabled = false;
  let randomEntry: Submission | null = null;
  let showRandom = false;

  const fetchFeed = async () => {
    try {
      feedError = '';
      const response = await fetch(`${API_BASE}/api/feed`);
      if (!response.ok) {
        throw new Error('Unable to load the feed.');
      }
      const data: Submission[] = await response.json();
      feed = data;
    } catch (error) {
      console.error(error);
      feedError = 'Unable to load the feed right now.';
    }
  };

  onMount(() => {
    fetchFeed();
  });

  const handleSubmit = async () => {
    if (!text.trim()) {
      errorMessage = 'Share something you learnt before submitting!';
      return;
    }

    loading = true;
    buttonDisabled = true;
    successMessage = '';
    errorMessage = '';

    try {
      const response = await fetch(`${API_BASE}/api/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: text.trim(),
          name: name.trim() ? name.trim() : null
        })
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? 'Submission failed.');
      }

      const result = await response.json();
      if (result.status === 'approved') {
        successMessage = 'Thanks for sharing! Your reflection is now live.';
      } else if (result.status === 'rejected') {
        successMessage = 'Thanks! Moderation flagged this one, feel free to try again.';
      } else {
        successMessage = 'Thanks! Your reflection will be reviewed shortly.';
      }

      text = '';
      name = '';
      await fetchFeed();
    } catch (error) {
      console.error(error);
      errorMessage = error instanceof Error ? error.message : 'Submission failed.';
    } finally {
      loading = false;
      setTimeout(() => {
        buttonDisabled = false;
      }, 2000);
    }
  };

  const fetchRandom = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/random`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('No reflections yet. Be the first to share!');
        }
        throw new Error('Could not fetch a reflection.');
      }
      randomEntry = await response.json();
      showRandom = true;
    } catch (error) {
      console.error(error);
      errorMessage = error instanceof Error ? error.message : 'Something went wrong.';
    }
  };

  const closeRandom = () => {
    showRandom = false;
    randomEntry = null;
  };
</script>

<div class="min-h-screen flex flex-col items-center px-4 py-16">
  <main class="w-full max-w-2xl space-y-12">
    <section class="text-center space-y-4">
      <h1 class="text-4xl font-semibold text-slate-900">What I Learnt in 2025</h1>
      <p class="text-slate-600">Share a quick reflection and browse what others discovered this year.</p>
    </section>

    <section class="bg-white rounded-2xl shadow-sm border border-slate-100 p-8 space-y-6">
      <form
        class="space-y-4"
        on:submit|preventDefault={handleSubmit}
      >
        <div class="space-y-2">
          <label class="block text-left text-sm font-medium text-slate-700" for="text">
            What did you learn in 2025?
          </label>
          <textarea
            id="text"
            class="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-slate-800 focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-200"
            rows="4"
            maxlength="280"
            bind:value={text}
            placeholder="I learnt that slowing down helped me reconnect with my creativity..."
            required
          ></textarea>
        </div>

        <div class="space-y-2">
          <label class="block text-left text-sm font-medium text-slate-700" for="name">
            Name (optional)
          </label>
          <input
            id="name"
            type="text"
            maxlength="80"
            class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-slate-800 focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-200"
            bind:value={name}
            placeholder="Add your name or keep it anonymous"
          />
        </div>

        {#if successMessage}
          <p class="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{successMessage}</p>
        {/if}

        {#if errorMessage}
          <p class="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{errorMessage}</p>
        {/if}

        <button
          type="submit"
          class="inline-flex w-full items-center justify-center rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={loading || buttonDisabled}
        >
          {#if loading}
            Sending...
          {:else}
            Share your learning
          {/if}
        </button>
      </form>

      <button
        type="button"
        class="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
        on:click={fetchRandom}
      >
        Inspire me with something random
      </button>
    </section>

    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold text-slate-800">Community reflections</h2>
        <button
          type="button"
          class="text-sm font-medium text-slate-500 hover:text-slate-700"
          on:click={fetchFeed}
        >
          Refresh
        </button>
      </div>

      {#if feedError}
        <p class="rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">{feedError}</p>
      {:else if feed.length === 0}
        <p class="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-8 text-center text-slate-500">
          No reflections yet. Be the first to share!
        </p>
      {:else}
        <ul class="space-y-4">
          {#each feed as item (item.text + item.date)}
            <li class="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <p class="text-base text-slate-900">{item.text}</p>
              <div class="mt-4 flex items-center justify-between text-sm text-slate-500">
                <span>{item.name ?? 'Anonymous'}</span>
                {#if item.date}
                  <span>{new Date(item.date).toLocaleString()}</span>
                {/if}
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </main>

  {#if showRandom && randomEntry}
    <div class="fixed inset-0 flex items-center justify-center bg-slate-900/60 px-4">
      <div class="w-full max-w-lg space-y-4 rounded-2xl bg-white p-6 shadow-xl">
        <div class="flex items-start justify-between">
          <h3 class="text-lg font-semibold text-slate-900">A random insight</h3>
          <button
            type="button"
            class="text-sm text-slate-400 transition hover:text-slate-600"
            on:click={closeRandom}
          >
            Close
          </button>
        </div>
        <p class="text-slate-800">{randomEntry.text}</p>
        <div class="text-sm text-slate-500">
          <span>{randomEntry.name ?? 'Anonymous'}</span>
          {#if randomEntry.date}
            <span class="ml-2">• {new Date(randomEntry.date).toLocaleString()}</span>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</div>
