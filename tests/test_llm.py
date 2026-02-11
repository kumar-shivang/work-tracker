from llm import summarize_diff

dummy_diff = """
diff --git a/main.py b/main.py
index e69de29..d95f3ad 100644
--- a/main.py
+++ b/main.py
@@ -1,5 +1,6 @@
 def hello():
-    print("Hello")
+    print("Hello World")
+    return True
"""

print("Sending dummy diff to LLM...")
summary = summarize_diff(dummy_diff)
print("\nSummary:")
print(summary)
