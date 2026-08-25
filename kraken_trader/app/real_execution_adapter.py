class RealExecutionDisabled(RuntimeError):pass
class RealExecutionAdapter:
 enabled=False
 def execute(self,plan):raise RealExecutionDisabled('Realausführung ist hart deaktiviert')
