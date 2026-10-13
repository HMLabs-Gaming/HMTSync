package de.jumpstone.plugins.commands;

import de.jumpstone.plugins.managers.DatabaseManager;
import de.jumpstone.plugins.utils.DataManagementGUI;
import org.bukkit.command.Command;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockmc.mockmc.MockMC;
import org.mockmc.mockmc.ServerMock;
import org.mockmc.mockmc.entity.PlayerMock;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class SyncCommandTest {

    private ServerMock server;
    private DatabaseManager mockDatabaseManager;
    private DataManagementGUI mockGuiManager;
    private Command mockCommand;

    @BeforeEach
    void setup() {
        server = MockMC.mock();
        mockDatabaseManager = mock(DatabaseManager.class);
        mockGuiManager = mock(DataManagementGUI.class);
        mockCommand = mock(Command.class);
    }

    @AfterEach
    void tearDown() {
        MockMC.unmock();
    }

    @Test
    void testTabCompletionSubcommands() {
        SyncCommand cmd = new SyncCommand(mockDatabaseManager, mockGuiManager);
        PlayerMock admin = server.addPlayer("AdminUser");
        admin.setOp(true);

        List<String> arg0Completions = cmd.onTabComplete(admin, mockCommand, "hmtsync", new String[]{""});
        assertNotNull(arg0Completions);
        assertTrue(arg0Completions.contains("unlock"));
        assertTrue(arg0Completions.contains("inspect"));
        assertTrue(arg0Completions.contains("invsee"));
        assertTrue(arg0Completions.contains("endersee"));
        assertTrue(arg0Completions.contains("migrate"));
    }

    @Test
    void testTabCompletionEditFlag() {
        SyncCommand cmd = new SyncCommand(mockDatabaseManager, mockGuiManager);
        PlayerMock admin = server.addPlayer("AdminUser");
        admin.setOp(true);

        List<String> invseeArg2 = cmd.onTabComplete(admin, mockCommand, "hmtsync", new String[]{"invsee", "TargetPlayer", "-"});
        assertNotNull(invseeArg2);
        assertTrue(invseeArg2.contains("--edit"));

        List<String> inspectArg3 = cmd.onTabComplete(admin, mockCommand, "hmtsync", new String[]{"inspect", "TargetPlayer", "inventory", "-"});
        assertNotNull(inspectArg3);
        assertTrue(inspectArg3.contains("--edit"));
    }

    @Test
    void testTabCompletionPlayerNames() {
        SyncCommand cmd = new SyncCommand(mockDatabaseManager, mockGuiManager);
        server.addPlayer("Alice");
        PlayerMock admin = server.addPlayer("Bob");
        admin.setOp(true);

        List<String> playerCompletions = cmd.onTabComplete(admin, mockCommand, "hmtsync", new String[]{"invsee", "Al"});
        assertNotNull(playerCompletions);
        assertTrue(playerCompletions.contains("Alice"));
    }
}
