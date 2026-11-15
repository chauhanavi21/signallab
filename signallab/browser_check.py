import re
from playwright.sync_api import expect
import json
from browser_support import run


def scenario(page, context, base, output, check):
    expect(page.locator('#status')).to_contain_text('replay complete')
    check("initial replay renders computed policies", page.locator("#comparison tbody tr").count()==3)
    check("burn chart rendered", page.locator("#chart svg path").count()==2)
    check("default incident episodes", page.locator("#alerts tbody tr").count()==2)
    page.select_option("#service", "search-api")
    check("service selection updates chart", "search-api" in page.locator("#chart svg").get_attribute("aria-label"))
    page.fill("#slo", "99.95")
    page.click("#run")
    expect(page.locator('#run')).to_be_enabled()
    with page.expect_download() as event: page.click("#export")
    download = event.value
    report = json.loads(download.path().read_text(encoding="utf-8"))
    check("configuration reaches calculation engine", abs(report["config"]["slo"]-.9995)<1e-10)
    check("export includes reproducible run hash", len(report["run_id"])==64)
    page.set_input_files("#csv-file", {"name":"invalid.csv", "mimeType":"text/csv", "buffer":b"minute,service,total,bad\n1,api,100,0\n"})
    expect(page.locator('#status')).to_have_class(re.compile('error'))
    check("invalid CSV has actionable error", "contiguous" in page.locator("#status").inner_text())
    page.set_input_files("#csv-file", {"name":"custom.csv", "mimeType":"text/csv", "buffer":b"minute,service,total,bad\n0,my-api,1000,2\n1,my-api,1000,0\n"})
    expect(page.locator('#status')).to_contain_text('Imported replay complete')
    check("imported data has no fabricated incident scores", page.locator("#label-state").inner_text()=="Unlabeled imported data" and "—" in page.locator("#comparison").inner_text())
    with page.expect_download() as event: page.click("#sample")
    check("sample download has exact CSV header", event.value.path().read_text(encoding="utf-8").startswith("minute,service,total,bad\n"))
    page.fill("#slo", "99.9")
    page.click("#reset")
    expect(page.locator('#status')).to_contain_text('Synthetic replay complete')
    check("demo can be restored after import", page.locator("#alerts tbody tr").count()==2)
    with page.expect_download() as event: page.click("#export")
    report = json.loads(event.value.path().read_text(encoding="utf-8"))
    from core import analyze
    check("browser and CLI default run hashes match", report["run_id"]==analyze()["run_id"])
    page.locator("#chart svg").focus()
    page.keyboard.press("End")
    check("chart keyboard inspection reaches the real final minute", "Minute 719" in page.locator("#chart-readout").inner_text())
    page.keyboard.press("ArrowLeft")
    check("chart keyboard inspection steps through request buckets", "Minute 718" in page.locator("#chart-readout").inner_text())
    check("hero service summaries come from the replay", page.locator(".service-signal").count()==report["summary"]["service_count"])


if __name__ == "__main__": run(scenario)
