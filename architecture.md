# Frontend Architecture Reference

## DOM Structure

```
<div id="app">
  <div id="sidebar">
    <div class="sidebar-header">      <!-- Logo, collapse button -->
    <input id="search-input">         <!-- Filter lessons -->
    <div id="tree-container">         <!-- Course tree -->
      <div class="tree-stage">        <!-- Each stage (collapsible) -->
        <div class="stage-header">    <!-- Stage name, progress count -->
        <div class="stage-lessons">   <!-- Lesson list -->
          <div class="lesson-node">   <!-- Each lesson (clickable) -->
            <span class="lesson-check">  <!-- Completion checkmark -->
            <span class="lesson-name">   <!-- Lesson title -->
            <span class="lesson-star">   <!-- Star icon -->
          </div>
  <main id="main-area">
    <div id="toolbar">               <!-- Top toolbar -->
      <button id="btn-theme">        <!-- Dark/light toggle -->
      <button id="btn-dashboard">    <!-- Dashboard overlay -->
      <button id="btn-starred">      <!-- Starred list -->
      <button id="btn-ai-summary">   <!-- AI summary panel -->
      <select id="speed-select">     <!-- Playback speed -->
      <span id="watch-time-display"> <!-- Watch time stats -->
    <div id="content-area">
      <div id="player-col">
        <div id="continue-watching"> <!-- Continue watching bar -->
        <div id="player-wrap">
          <div class="player-empty"> <!-- Empty state -->
          <video id="video-player">  <!-- HTML5 video -->
        <div id="playlist-bar">      <!-- Playlist navigation -->
      <div id="notes-col">           <!-- Notes/annotations panel -->
  <div id="dashboard-panel">         <!-- Full-screen overlay -->
    <div class="dash-grid">          <!-- Stats cards -->
    <div class="goal-input-wrap">    <!-- Daily goal settings -->
    <div id="stage-progress-list">   <!-- Per-stage progress bars -->
    <div id="starred-list">          <!-- Starred lessons (chips) -->
    <div id="history-list">          <!-- Watch history items -->
  <div id="ai-summary-panel">        <!-- AI summary overlay -->
```

## CSS Architecture

### Theme System
All colors use CSS custom properties. Switch themes via `data-theme` attribute on `<html>`:
```css
:root, [data-theme="dark"] { --bg: #0c0c14; --accent: #6366f1; ... }
[data-theme="light"] { --bg: #f8f7f3; --accent: #4f46e5; ... }
```

### Key CSS Sections (by comment markers)
1. **Base & Reset** — Typography, scrollbar, transitions
2. **Sidebar** — Tree styling, lesson nodes, stage collapse
3. **Video Player** — Player, playlist bar, player overlay
4. **Notes Panel** — Annotations, highlights, resize handle
5. **Dashboard Panel** — Cards grid, stage progress, starred chips, history list
6. **Continue Watching Bar** — Gradient banner with lesson info
7. **AI Summary Panel** — Summary display, quiz cards, progress bar
8. **Toast** — Notification toasts (`.toast`, `.toast.show`)
9. **Responsive** — Mobile breakpoints

### Dashboard Cards
`.dash-grid` uses CSS grid (auto-fill, minmax). Each `.dash-card` shows a stat.

### History Items
`.history-item` — flex row with icon, name, meta (stage + relative time), progress percentage.

## JavaScript Flow

### Initialization (`init()`)
1. `loadState()` — Restore from localStorage
2. `validateBootstrap()` — Verify required functions exist
3. `fetch('course-data.json')` — Load course tree into `COURSE_TREE`
4. Apply theme, notes visibility, goal settings
5. `renderTree()` + `renderDashboard()` + `renderContinueWatching()`

### Lesson Selection (`selectLesson(lesson)`)
1. Set `state.currentLesson` and `state.currentPlaylist`
2. Call `playVideo(videos[0], 0, videos.length, lesson.name)`
3. Load notes and annotations
4. Start watch tracking interval

### Video Playback (`playVideo(src, idx, total, title)`)
1. Stop old tracking timer
2. Calculate `savedPos` (only for `idx === 0`)
3. Pause, reset `currentTime`, set new `src`
4. Restore position on `loadedmetadata`
5. Update playlist bar UI
6. Call `pushHistory()` + `renderContinueWatching()`
7. `videoPlayer.play()`

### Auto-play Chain
On `video.ended` event:
1. `playNextInPlaylist()` — Advance within current lesson's playlist
2. If last video: mark lesson completed, `autoPlayNext()` — Jump to next lesson

### State Persistence
- `saveState()` serializes to localStorage on every meaningful change
- `summaries` also backed up to server via `POST /api/summaries`
- `watchHistory` array: max 50 entries, deduped by `lessonId`

## Extending the Frontend

### Adding a New Panel
1. Add HTML in `<div id="content-area">` as a sibling overlay
2. Add CSS following the dashboard panel pattern (`position: absolute`, `backdrop-filter`)
3. Add toggle button in `#toolbar`
4. Add event listener in UI ACTIONS section
5. Toggle `.visible` class to show/hide

### Adding a New State Field
1. Add to `state` object with default value
2. Add to `loadState()`: `state.newField = s.newField || defaultValue`
3. Add to `saveState()`: `newField: state.newField`
4. Use in rendering functions
