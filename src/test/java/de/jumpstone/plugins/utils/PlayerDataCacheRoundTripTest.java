package de.jumpstone.plugins.utils;

import de.jumpstone.plugins.HMTSync;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Covers the JSON round trip the hybrid Redis cache relies on: one server
 * serialises a committed snapshot, the next server restores it and applies it
 * without touching SQL.
 */
public class PlayerDataCacheRoundTripTest {

    @Test
    void restoresSnapshotFromCachedJson() {
        PlayerData original = new PlayerData();
        original.setHealth(17.5);
        original.setFoodLevel(11);
        original.setLevel(42);
        original.setGameMode("CREATIVE");
        original.setWorld("world");
        original.setX(128.5);
        original.setInventoryContentsNBT(java.util.Collections.singletonList("{}"));

        String json = HMTSync.getGson().toJson(original);
        PlayerData restored = PlayerData.fromJson(json);

        assertNotNull(restored, "a committed payload must round trip through the cache");
        assertEquals(17.5, restored.getHealth(), 0.0001);
        assertEquals(11, restored.getFoodLevel());
        assertEquals(42, restored.getLevel());
        assertEquals("CREATIVE", restored.getGameMode());
        assertEquals("world", restored.getWorld());
        assertEquals(128.5, restored.getX(), 0.0001);
        assertEquals(1, restored.getInventoryContentsNBT().size());
    }

    @Test
    void preservesThirdPartyBridgeFields() {
        PlayerData original = new PlayerData();
        original.setEconomyBalance(1234.75);
        original.setPlaytimeMinutes(987);

        PlayerData restored = PlayerData.fromJson(HMTSync.getGson().toJson(original));

        assertNotNull(restored);
        assertEquals(1234.75, restored.getEconomyBalance(), 0.0001);
        assertEquals(987, restored.getPlaytimeMinutes());
    }

    @Test
    void rejectsUnusablePayloadsSoTheCallerFallsBackToSql() {
        assertNull(PlayerData.fromJson(null), "an absent cache entry must report a miss");
        assertNull(PlayerData.fromJson(""), "an empty cache entry must report a miss");
        assertNull(PlayerData.fromJson("   "), "a blank cache entry must report a miss");
        assertNull(PlayerData.fromJson("not json at all"), "a corrupt entry must report a miss");
    }

    @Test
    void roundTripKeepsSnapshotChecksumStable() {
        // The checksum gates save rejection downstream, so the same logical
        // snapshot must serialise identically every time it is cached.
        PlayerData data = new PlayerData();
        data.setHealth(10.0);
        data.setFoodLevel(20);
        data.setInventoryContentsNBT(java.util.Collections.singletonList("{}"));

        String first = HMTSync.getGson().toJson(data);
        String second = HMTSync.getGson().toJson(PlayerData.fromJson(first));

        assertEquals(first, second, "caching must not perturb the payload");
        assertTrue(first.contains("inventoryContentsNBT"));
    }
}
