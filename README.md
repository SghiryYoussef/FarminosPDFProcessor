# FarminOS Invoice  Script



##  How to Run

1. **Install dependencies**  
   Run this in your shell:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. **Run the script**
   ```bash
   python main.py
   ```

##  Output

The cleaned invoices will be saved in the `all_modified_invoices/` folder.

##  Requirements

Make sure your `requirements.txt` includes:
```
playwright
asyncio
pathlib
datetime

```

##  Notes

- The script uses the staging login and credentials provided.
  

