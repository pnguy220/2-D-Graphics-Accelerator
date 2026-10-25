module framebuffer (
    input logic clk,

    // Write port
    input logic wr_en,
    input logic [11:0] wr_addr,
    input logic [7:0]  wr_data,

    // Read port
    input  logic [11:0] rd_addr,
    output logic [7:0]  rd_data
);

    // Memory declaration goes here
    logic [7:0] memory [0:4095];
  
    always_ff @(posedge clk)begin
        rd_data <= memory[rd_addr];// Synchronous read logic
        if(wr_en)
        memory[wr_addr] <= wr_data;  // Synchronous write logic
    end

    

endmodule