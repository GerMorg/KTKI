"""Single source of truth for the v100 Real-Handel status used by every GUI surface."""
def _flag(db,key,default=False):
    return str(db.value(key,"true" if default else "false")).strip().lower()=="true"

def build_real_state(db,controller):
    automation_master=_flag(db,"automation_master_enabled",True)
    real_enabled=_flag(db,"real_trading_enabled",False)
    kill_clear=not _flag(db,"real_kill_switch",True)
    real_auto=_flag(db,"automation_real_enabled",False)
    real_execute=_flag(db,"automation_real_execute_enabled",False)

    blockers=[]
    if not real_enabled:
        blockers.append({"code":"REAL_TRADING_DISABLED","reason":"Realhandel ist in der Home-Assistant-Konfiguration deaktiviert."})
    if not kill_clear:
        blockers.append({"code":"REAL_KILL_SWITCH_ACTIVE","reason":"Der Realhandels-Kill-Switch ist aktiv."})

    manual_order_available=real_enabled and kill_clear
    automatic_execution_ready=manual_order_available and automation_master and real_auto and real_execute

    automatic_blockers=[]
    if not automation_master:
        automatic_blockers.append("Gesamtautomatik ist deaktiviert.")
    if not real_auto:
        automatic_blockers.append("Real-Automatik ist deaktiviert.")
    if not real_execute:
        automatic_blockers.append("Automatische Real-Ausführung ist deaktiviert.")

    if automatic_execution_ready:
        status_label="REALHANDEL FREIGEGEBEN"
        summary="Realhandel ist global freigegeben; die automatische Real-Ausführung ist ebenfalls freigeschaltet."
    elif manual_order_available:
        status_label="REALHANDEL BASIS AKTIV"
        summary="Reale Orders sind grundsätzlich freigegeben, die automatische Real-Ausführung ist jedoch nicht vollständig aktiviert."
    else:
        status_label="REALHANDEL BLOCKIERT"
        summary="Mindestens eine globale Realhandels-Sperre ist aktiv."

    return {
        "global_real_enabled":real_enabled,
        "kill_switch_clear":kill_clear,
        "automation_master_enabled":automation_master,
        "real_automation_enabled":real_auto,
        "real_execute_enabled":real_execute,
        "manual_order_available":manual_order_available,
        "automatic_execution_ready":automatic_execution_ready,
        "status_label":status_label,
        "summary":summary,
        "automatic_summary":" ".join(automatic_blockers) if automatic_blockers else "Alle globalen Voraussetzungen der automatischen Real-Ausführung sind erfüllt.",
        "blockers":blockers,
    }
