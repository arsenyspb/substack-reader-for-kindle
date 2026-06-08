import pytest
from src.media_engine import MediaEngine

def test_media_engine_removes_forms():
    """
    RED: Test that MediaEngine removes <form> tags. 
    Currently, it only removes script, style, hr, and button.
    """
    engine = MediaEngine()
    raw_html = """
    <html>
        <body>
            <div class="markup">
                <h1>Title</h1>
                <form action="/submit">
                    <input type="text" name="name">
                    <button type="submit">Submit</button>
                </form>
                <p>Content</p>
            </div>
        </body>
    </html>
    """
    sanitized_html, assets = engine.process_content(raw_html)
    
    # Assert that <form> tag is NOT in the sanitized output
    assert "<form" not in sanitized_html
    assert "Submit" not in sanitized_html # button is already removed
