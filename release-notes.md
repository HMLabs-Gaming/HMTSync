# Release Notes - v1.0.2

**HMT Sync v1.0.2** - **Minecraft 26.3 Compatibility & Hybrid Platform Support**

This release rebrands the plugin from *MC Data Bridge* to **HMT Sync** and adds
first-class support for Minecraft 26.3, Redis-backed caching, and hybrid builds
for Paper/Spigot and Velocity.

---

### ✨ Features
*   **Minecraft 26.3 Support:** Updated to Paper API `26.3.build.42-alpha`, targeting Minecraft 26.3 (Java 25). Plugin metadata now declares `api-version: '26.3'`.
*   **Hybrid Builds:** Separate build profiles produce dedicated JARs for Spigot/Paper (`-spigot`) and Velocity (`-velocity`), plus a combined `-universal` JAR for single-file distribution on CurseForge/SpigotMC.
*   **Redis Integration:** Hybrid Redis-MySQL caching layer to reduce database load and speed up cross-server synchronization.
*   **Economy & Playtime Sync:** Optional synchronization of economy balances and playtime across servers.

### 🐛 Bug Fixes
*   **Fixed Kick on Server Switch with High Health:** Players with health greater than 20.0 (Health Boost) are no longer kicked with an `IllegalArgumentException`. Potions and attributes are loaded before the max-health attribute is applied.
