# HMT Sync Build Guide

This guide explains how to build the HMT Sync plugin for different Minecraft server platforms.

## Building for Different Platforms

### 1. Building for Spigot/Paper Servers (Recommended for game servers)

```bash
mvn clean package -Pspigot
```

This creates: `target/hmt-sync-1.0.3-spigot.jar`

**Use this JAR for:**

- Spigot servers
- Paper servers
- Any Bukkit-compatible server

### 2. Building for Velocity Proxies

```bash
mvn clean package -Pvelocity
```

This creates: `target/hmt-sync-1.0.3-velocity.jar`

**Use this JAR for:**

- Velocity proxy servers

### 3. Building for BungeeCord Proxies

```bash
mvn clean package -Pbungee
```

This creates: `target/hmt-sync-1.0.3-bungee.jar`

**Use this JAR for:**

- BungeeCord proxy servers
- Waterfall servers

### 4. Building Universal JAR (Development only)

```bash
mvn clean package -Puniversal
```

This creates: `target/hmt-sync-1.0.3-universal.jar`

**Warning:** This JAR contains all metadata files and should only be used for development/testing. It may cause conflicts on production servers.

## Deployment Instructions

### For Game Servers (Spigot/Paper):

1. Build using `-Pspigot` profile
2. Copy `hmt-sync-*-spigot.jar` to your server's `plugins/` folder
3. Restart the server

### For Proxy Servers:

1. **For Velocity:** Build using `-Pvelocity` profile
2. **For BungeeCord:** Build using `-Pbungee` profile
3. Copy the appropriate JAR to your proxy's `plugins/` folder
4. Restart the proxy

## Troubleshooting

### "Unable to load plugin - appears to be a Bukkit or BungeeCord plugin"

This error occurs when you try to load a Bukkit-formatted plugin on Velocity, or vice versa.

**Solution:**

- Make sure you're using the correct build profile for your platform
- Don't use the universal JAR on production servers
- Check that you built with the correct Maven profile

### Checking Which JAR You Have

You can verify which platform a JAR is built for by examining its contents:

```bash
# Check if it's a Spigot JAR (should contain plugin.yml)
jar -tf target/hmt-sync-*-spigot.jar | grep plugin.yml

# Check if it's a BungeeCord JAR (should contain bungee.yml)
jar -tf target/hmt-sync-*-bungee.jar | grep bungee.yml

# Velocity JARs should NOT contain plugin.yml or bungee.yml
jar -tf target/hmt-sync-*-velocity.jar | grep -E "(plugin\.yml|bungee\.yml)"
```

## Why This Structure?

The hybrid approach requires different metadata files because:

- **Spigot/Paper** uses `plugin.yml` format
- **BungeeCord** uses `bungee.yml` format
- **Velocity** uses annotation-based plugin definition (no YAML file needed)

Each platform's loader checks for its specific metadata format, which is why mixing them causes loading errors.

## Requirements

- **JDK 25** (the `maven.compiler.release` target is 25; older JDKs cannot build this project)
- **Maven 3.9+**

## Test Fixtures

### MockMC registry data

Most tests boot a full mock Bukkit server through
[`MockMC`](https://github.com/SecondLifeGaming/mockmc). MockMC ships its registry
data inside its own JAR, generated against Paper 26.2, while this plugin targets
Paper 26.3. Every registry entry that 26.3 added is therefore missing, and the
first static initialiser that asks for one (`ItemType`, `BlockType`, `Sound`,
`Biome`, ...) throws `NoSuchElementException`, which cascades into every
MockMC-backed test erroring out.

`src/test/resources/keyed/*.json` are 26.3-complete copies of those files. MockMC
reads them with `getResourceAsStream("/keyed/<id>.json")`, so the test resources
shadow the copies inside the dependency JAR. They are generated, not hand-edited:

```bash
python3 scripts/gen_mockmc_26_3_registry.py
```

The script reads the real `paper-api` 26.2 and 26.3 JARs, diffs the enum
constants, and for each new key clones the most similar existing entry and
retargets every self-reference inside it (key, `translationKey`, `typed`,
`material`, `blockType`, `item_model`, …). Sound keys are not derivable from the
constant name (`BLOCK_STRAW_BED_BREAK_LEAVE` is
`minecraft:block.straw_bed.break_leave`), so they are read straight out of the
`Sound` class's `<clinit>`, where each key is a literal next to its `putstatic`.

**Regenerate these whenever the Paper version in `pom.xml` changes.** If a Paper
upgrade adds registry content the fixtures do not cover, the affected tests will
fail with `No value for minecraft:<key>`; rerun the script and commit the result.
